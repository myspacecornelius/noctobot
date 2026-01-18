"""
Unified Monitor Manager
Orchestrates all monitor types and integrates with the bot engine
"""

import asyncio
from typing import Optional, List, Dict, Any, Callable, Awaitable
from datetime import datetime
from dataclasses import dataclass, field
import structlog

from .shopify_monitor import MultiStoreMonitor, DetectedProduct, create_default_monitor
from .footsites import MultiFootsiteMonitor
from .products import product_db, CuratedProduct
from .base import ProductInfo

logger = structlog.get_logger()


@dataclass
class MonitorEvent:
    """Event from any monitor"""
    event_type: str  # "new_product", "restock", "price_drop"
    source: str  # "shopify", "footsite", "snkrs"
    store_name: str
    product: ProductInfo
    matched_product: Optional[CuratedProduct] = None
    match_confidence: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    
    @property
    def is_profitable(self) -> bool:
        if self.matched_product:
            return self.matched_product.is_profitable
        return False
    
    @property
    def priority(self) -> str:
        if self.matched_product:
            return self.matched_product.priority
        return "low"


class MonitorManager:
    """
    Unified monitor manager that coordinates all monitor types
    
    Features:
    - Multi-platform monitoring (Shopify, Footsites, SNKRS)
    - Unified event handling
    - Auto-task creation on product detection
    - Priority-based alerting
    - Curated product matching
    """
    
    def __init__(self):
        self.shopify_monitor: Optional[MultiStoreMonitor] = None
        self.footsite_monitor: Optional[MultiFootsiteMonitor] = None
        
        self._running = False
        self._events: List[MonitorEvent] = []
        self._max_events = 1000
        
        # Callbacks
        self._on_event: Optional[Callable[[MonitorEvent], Awaitable[None]]] = None
        self._on_high_priority: Optional[Callable[[MonitorEvent], Awaitable[None]]] = None
        
        # Configuration
        self.auto_task_enabled = False
        self.auto_task_min_confidence = 0.7
        self.auto_task_min_priority = "medium"
        
        # Stats
        self.total_products_found = 0
        self.high_priority_found = 0
        self.tasks_created = 0
        
        logger.info("MonitorManager initialized")
    
    def setup_shopify(
        self,
        stores: Optional[List[Dict]] = None,
        target_sizes: Optional[List[str]] = None,
        use_defaults: bool = True
    ):
        """Set up Shopify monitoring"""
        if use_defaults and not stores:
            self.shopify_monitor = create_default_monitor(target_sizes)
        else:
            self.shopify_monitor = MultiStoreMonitor()
            if stores:
                self.shopify_monitor.add_stores_from_list(stores)
        
        # Set callback
        self.shopify_monitor.set_product_callback(self._handle_shopify_product)
        
        logger.info("Shopify monitoring configured", 
                   store_count=len(self.shopify_monitor.stores))
    
    def setup_footsites(
        self,
        sites: Optional[List[str]] = None,
        keywords: Optional[List[str]] = None,
        target_sizes: Optional[List[str]] = None,
        delay_ms: int = 5000
    ):
        """Set up Footsite monitoring"""
        # Build keywords from curated products if not provided
        if not keywords:
            keywords = self._build_keywords_from_db()
        
        self.footsite_monitor = MultiFootsiteMonitor(
            sites=sites or ["footlocker", "champs", "eastbay"],
            keywords=keywords,
            target_sizes=target_sizes,
            delay_ms=delay_ms
        )
        
        self.footsite_monitor.set_callback(self._handle_footsite_product)
        
        logger.info("Footsite monitoring configured",
                   sites=sites or ["footlocker", "champs", "eastbay"],
                   keyword_count=len(keywords))
    
    def _build_keywords_from_db(self) -> List[str]:
        """Build search keywords from curated product database"""
        keywords = set()
        
        for product in product_db.get_enabled():
            # Add key positive keywords
            for kw in product.positive_keywords[:3]:
                keywords.add(kw)
        
        return list(keywords)[:20]  # Limit to top 20
    
    def set_event_callback(self, callback: Callable[[MonitorEvent], Awaitable[None]]):
        """Set callback for all monitor events"""
        self._on_event = callback
    
    def set_high_priority_callback(self, callback: Callable[[MonitorEvent], Awaitable[None]]):
        """Set callback for high priority events only"""
        self._on_high_priority = callback
    
    def enable_auto_tasks(
        self,
        enabled: bool = True,
        min_confidence: float = 0.7,
        min_priority: str = "medium"
    ):
        """Enable automatic task creation for matching products"""
        self.auto_task_enabled = enabled
        self.auto_task_min_confidence = min_confidence
        self.auto_task_min_priority = min_priority
        
        logger.info("Auto-task creation configured",
                   enabled=enabled,
                   min_confidence=min_confidence,
                   min_priority=min_priority)
    
    async def start(self):
        """Start all monitors"""
        if self._running:
            logger.warning("MonitorManager already running")
            return
        
        self._running = True
        
        # Load curated products
        product_db.load_builtin()
        
        tasks = []
        
        if self.shopify_monitor:
            tasks.append(self.shopify_monitor.start())
        
        if self.footsite_monitor:
            tasks.append(self.footsite_monitor.start())
        
        if tasks:
            await asyncio.gather(*tasks)
        
        logger.info("MonitorManager started")
    
    async def stop(self):
        """Stop all monitors"""
        if not self._running:
            return
        
        self._running = False
        
        tasks = []
        
        if self.shopify_monitor:
            tasks.append(self.shopify_monitor.stop())
        
        if self.footsite_monitor:
            tasks.append(self.footsite_monitor.stop())
        
        if tasks:
            await asyncio.gather(*tasks)
        
        logger.info("MonitorManager stopped")
    
    async def _handle_shopify_product(self, detected: DetectedProduct):
        """Handle product from Shopify monitor"""
        event = MonitorEvent(
            event_type="new_product" if not detected.is_restock else "restock",
            source="shopify",
            store_name=detected.store.name,
            product=detected.info,
            matched_product=detected.matched_curated,
            match_confidence=detected.match_confidence
        )
        
        await self._process_event(event)
    
    async def _handle_footsite_product(self, site: str, product: ProductInfo):
        """Handle product from Footsite monitor"""
        # Try to match against curated products
        matches = product_db.match_product_title(product.title)
        matched = None
        confidence = 0.0
        
        if matches:
            matched, confidence = matches[0]
        
        event = MonitorEvent(
            event_type="new_product",
            source="footsite",
            store_name=site,
            product=product,
            matched_product=matched,
            match_confidence=confidence
        )
        
        await self._process_event(event)
    
    async def _process_event(self, event: MonitorEvent):
        """Process a monitor event"""
        self.total_products_found += 1
        
        # Store event
        self._events.append(event)
        if len(self._events) > self._max_events:
            self._events = self._events[-self._max_events:]
        
        # Log event
        logger.info(
            "Monitor event",
            type=event.event_type,
            source=event.source,
            store=event.store_name,
            product=event.product.title[:50],
            matched=event.matched_product.name if event.matched_product else None,
            confidence=f"{event.match_confidence:.2f}" if event.match_confidence else None,
            priority=event.priority
        )
        
        # Check if high priority
        is_high_priority = (
            event.priority == "high" or
            (event.matched_product and event.matched_product.profit_dollar > 100)
        )
        
        if is_high_priority:
            self.high_priority_found += 1
            
            if self._on_high_priority:
                await self._on_high_priority(event)
        
        # Fire general callback
        if self._on_event:
            await self._on_event(event)
        
        # Auto-create task if enabled
        if self.auto_task_enabled and self._should_create_task(event):
            await self._create_auto_task(event)
    
    def _should_create_task(self, event: MonitorEvent) -> bool:
        """Check if we should auto-create a task for this event"""
        if not event.matched_product:
            return False
        
        if event.match_confidence < self.auto_task_min_confidence:
            return False
        
        priority_levels = {"low": 0, "medium": 1, "high": 2}
        min_level = priority_levels.get(self.auto_task_min_priority, 1)
        event_level = priority_levels.get(event.priority, 0)
        
        return event_level >= min_level
    
    async def _create_auto_task(self, event: MonitorEvent):
        """Create an automatic task for a detected product"""
        # This would integrate with TaskManager
        # For now, just log it
        self.tasks_created += 1
        
        logger.info(
            "Auto-task would be created",
            product=event.product.title[:50],
            store=event.store_name,
            url=event.product.url,
            sizes=event.product.sizes_available[:5]
        )
    
    def add_shopify_store(
        self,
        name: str,
        url: str,
        delay_ms: int = 3000,
        target_sizes: Optional[List[str]] = None
    ):
        """Add a Shopify store to monitor"""
        if not self.shopify_monitor:
            self.shopify_monitor = MultiStoreMonitor()
            self.shopify_monitor.set_product_callback(self._handle_shopify_product)
        
        self.shopify_monitor.add_store(name, url, delay_ms, target_sizes)
    
    def update_footsite_keywords(self, keywords: List[str]):
        """Update Footsite search keywords"""
        if self.footsite_monitor:
            self.footsite_monitor.set_keywords(keywords)
    
    def load_products_from_json(self, path: str) -> int:
        """Load curated products from JSON file"""
        return product_db.load_from_json(path)
    
    def get_recent_events(self, limit: int = 50) -> List[MonitorEvent]:
        """Get recent monitor events"""
        return self._events[-limit:]
    
    def get_high_priority_events(self, limit: int = 20) -> List[MonitorEvent]:
        """Get recent high priority events"""
        high_priority = [e for e in self._events if e.priority == "high"]
        return high_priority[-limit:]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get monitoring statistics"""
        stats = {
            "running": self._running,
            "total_products_found": self.total_products_found,
            "high_priority_found": self.high_priority_found,
            "tasks_created": self.tasks_created,
            "events_stored": len(self._events),
            "curated_products": product_db.get_stats(),
        }
        
        if self.shopify_monitor:
            stats["shopify"] = self.shopify_monitor.get_stats()
        
        if self.footsite_monitor:
            stats["footsites"] = self.footsite_monitor.get_stats()
        
        return stats
    
    def get_curated_product_stats(self) -> Dict:
        """Get curated product database stats"""
        return product_db.get_stats()


# Global monitor manager
monitor_manager = MonitorManager()


async def quick_start_monitors(
    target_sizes: Optional[List[str]] = None,
    shopify: bool = True,
    footsites: bool = True,
    keywords_json: Optional[str] = None
) -> MonitorManager:
    """
    Quick start function to set up and run monitors
    
    Args:
        target_sizes: Sizes to monitor (e.g., ["10", "10.5", "11"])
        shopify: Enable Shopify monitoring
        footsites: Enable Footsite monitoring
        keywords_json: Path to curated keywords JSON file
    
    Returns:
        Configured and running MonitorManager
    """
    manager = MonitorManager()
    
    # Load curated products
    if keywords_json:
        manager.load_products_from_json(keywords_json)
    else:
        product_db.load_builtin()
    
    # Set up monitors
    if shopify:
        manager.setup_shopify(target_sizes=target_sizes, use_defaults=True)
    
    if footsites:
        manager.setup_footsites(target_sizes=target_sizes)
    
    # Start monitoring
    await manager.start()
    
    return manager
