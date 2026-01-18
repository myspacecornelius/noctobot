"""
Shopify Product Monitor - Production Ready
Comprehensive monitoring for Shopify-based stores
"""

import asyncio
import time
import hashlib
import random
import re
from typing import Optional, List, Dict, Set, Callable, Awaitable, Tuple
from datetime import datetime
from dataclasses import dataclass, field
import httpx
import structlog

from .base import MonitorResult, ProductInfo
from .products import CuratedProduct, product_db

logger = structlog.get_logger()


@dataclass
class MonitoredStore:
    """A Shopify store being monitored"""
    name: str
    url: str
    enabled: bool = True
    delay_ms: int = 3000
    proxy_group: Optional[str] = None
    
    # State
    last_check: Optional[datetime] = None
    last_hash: Optional[str] = None
    error_count: int = 0
    success_count: int = 0
    products_found: int = 0


@dataclass
class DetectedProduct:
    """A product detected by the monitor"""
    info: ProductInfo
    store: MonitoredStore
    matched_curated: Optional[CuratedProduct] = None
    match_confidence: float = 0.0
    is_restock: bool = False
    new_sizes: List[str] = field(default_factory=list)
    detected_at: datetime = field(default_factory=datetime.now)


class ShopifyStoreMonitor:
    """
    Monitors a single Shopify store for product changes
    
    Detection methods:
    1. products.json - Full catalog scraping
    2. Atom feed - Faster new product detection
    3. Sitemap - Backup discovery method
    """
    
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    ]
    
    def __init__(
        self,
        store: MonitoredStore,
        target_sizes: Optional[List[str]] = None,
        proxy_url: Optional[str] = None
    ):
        self.store = store
        self.target_sizes = self._normalize_sizes(target_sizes or [])
        self.proxy_url = proxy_url
        self.base_url = store.url.rstrip('/')
        
        # Session
        self._session: Optional[httpx.AsyncClient] = None
        
        # State tracking
        self._seen_products: Dict[str, ProductInfo] = {}
        self._seen_variants: Dict[str, Set[int]] = {}
        self._last_hash: Optional[str] = None
        
        # Rate limiting
        self._last_request_time = 0.0
        self._consecutive_errors = 0
        self._backoff_until = 0.0
    
    def _normalize_sizes(self, sizes: List[str]) -> List[str]:
        """Normalize size strings for comparison"""
        normalized = []
        for size in sizes:
            s = str(size).strip().upper()
            s = s.replace("US", "").replace("SIZE", "").replace("M", "").replace("W", "").strip()
            normalized.append(s)
        return normalized
    
    async def _get_session(self) -> httpx.AsyncClient:
        """Get or create HTTP session with rotation"""
        if self._session is None or self._session.is_closed:
            proxies = {"all://": self.proxy_url} if self.proxy_url else None
            
            self._session = httpx.AsyncClient(
                timeout=15.0,
                follow_redirects=True,
                proxies=proxies,
                headers={
                    "User-Agent": random.choice(self.USER_AGENTS),
                    "Accept": "application/json, text/plain, */*",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                }
            )
        return self._session
    
    async def check(self) -> MonitorResult:
        """Perform a single check of the store"""
        # Check backoff
        if time.time() < self._backoff_until:
            return MonitorResult(success=False, error="Backing off", rate_limited=True)
        
        # Rate limit
        elapsed = time.time() - self._last_request_time
        min_delay = self.store.delay_ms / 1000
        if elapsed < min_delay:
            await asyncio.sleep(min_delay - elapsed)
        
        self._last_request_time = time.time()
        start_time = time.time()
        
        try:
            session = await self._get_session()
            
            # Fetch products.json with pagination
            all_products = []
            page = 1
            
            while True:
                url = f"{self.base_url}/products.json?limit=250&page={page}"
                response = await session.get(url)
                
                if response.status_code == 429:
                    self._handle_rate_limit()
                    return MonitorResult(
                        success=False,
                        error="Rate limited",
                        rate_limited=True,
                        response_time=time.time() - start_time
                    )
                
                if response.status_code == 401 or response.status_code == 403:
                    self._consecutive_errors += 1
                    return MonitorResult(
                        success=False,
                        error=f"Access denied ({response.status_code})",
                        response_time=time.time() - start_time
                    )
                
                if response.status_code != 200:
                    self._consecutive_errors += 1
                    return MonitorResult(
                        success=False,
                        error=f"HTTP {response.status_code}",
                        response_time=time.time() - start_time
                    )
                
                data = response.json()
                products = data.get("products", [])
                
                if not products:
                    break
                
                all_products.extend(products)
                page += 1
                
                # Safety limit
                if page > 10:
                    break
                
                # Small delay between pages
                await asyncio.sleep(0.1)
            
            # Reset error count on success
            self._consecutive_errors = 0
            self.store.success_count += 1
            self.store.last_check = datetime.now()
            
            # Parse and check for changes
            detected = self._process_products(all_products)
            
            return MonitorResult(
                success=True,
                products=detected,
                response_time=time.time() - start_time
            )
            
        except httpx.TimeoutException:
            self._consecutive_errors += 1
            return MonitorResult(
                success=False,
                error="Request timeout",
                response_time=time.time() - start_time
            )
        except Exception as e:
            self._consecutive_errors += 1
            logger.error("Monitor error", store=self.store.name, error=str(e))
            return MonitorResult(
                success=False,
                error=str(e),
                response_time=time.time() - start_time
            )
    
    def _handle_rate_limit(self):
        """Handle rate limiting with exponential backoff"""
        backoff_time = min(300, 10 * (2 ** self._consecutive_errors))
        self._backoff_until = time.time() + backoff_time
        self._consecutive_errors += 1
        self.store.error_count += 1
        logger.warning(
            "Rate limited, backing off",
            store=self.store.name,
            backoff_seconds=backoff_time
        )
    
    def _process_products(self, products_data: List[Dict]) -> List[ProductInfo]:
        """Process products and detect new/restocked items"""
        detected = []
        
        for product in products_data:
            try:
                product_id = str(product.get("id", ""))
                title = product.get("title", "")
                handle = product.get("handle", "")
                
                # Get variants
                variants = product.get("variants", [])
                available_variants = [v for v in variants if v.get("available", False)]
                
                if not available_variants:
                    # Product went OOS - update state but don't report
                    if product_id in self._seen_products:
                        self._seen_variants[product_id] = set()
                    continue
                
                # Extract available sizes
                sizes_available = []
                variant_map = {}
                
                for variant in available_variants:
                    variant_id = variant.get("id")
                    size = self._extract_size(variant)
                    
                    if size:
                        sizes_available.append(size)
                        variant_map[size] = {
                            "id": variant_id,
                            "price": float(variant.get("price", 0)),
                            "sku": variant.get("sku", ""),
                            "inventory": variant.get("inventory_quantity", 0),
                        }
                
                # Filter by target sizes if specified
                if self.target_sizes:
                    matching_sizes = [s for s in sizes_available if s in self.target_sizes]
                    if not matching_sizes:
                        continue
                    sizes_available = matching_sizes
                
                # Get image
                images = product.get("images", [])
                image_url = images[0].get("src") if images else None
                
                # Get price
                price = float(available_variants[0].get("price", 0))
                
                # Build ProductInfo
                product_info = ProductInfo(
                    url=f"{self.base_url}/products/{handle}",
                    title=title,
                    sku=variants[0].get("sku") if variants else None,
                    price=price,
                    image_url=image_url,
                    available=True,
                    sizes_available=sizes_available,
                    variants=variant_map,
                    raw_data=product,
                    timestamp=datetime.now()
                )
                
                # Check if new or restock
                current_variant_ids = {v.get("id") for v in available_variants}
                
                if product_id not in self._seen_products:
                    # New product!
                    self._seen_products[product_id] = product_info
                    self._seen_variants[product_id] = current_variant_ids
                    detected.append(product_info)
                    self.store.products_found += 1
                    logger.info(
                        "New product detected",
                        store=self.store.name,
                        title=title[:50],
                        sizes=sizes_available[:5]
                    )
                else:
                    # Check for restock (new variants available)
                    old_variants = self._seen_variants.get(product_id, set())
                    new_variants = current_variant_ids - old_variants
                    
                    if new_variants:
                        # Restock detected!
                        self._seen_variants[product_id] = current_variant_ids
                        self._seen_products[product_id] = product_info
                        detected.append(product_info)
                        logger.info(
                            "Restock detected",
                            store=self.store.name,
                            title=title[:50],
                            new_variant_count=len(new_variants)
                        )
                
            except Exception as e:
                logger.warning("Failed to process product", error=str(e))
                continue
        
        return detected
    
    def _extract_size(self, variant: Dict) -> Optional[str]:
        """Extract and normalize size from variant"""
        # Try option fields
        for option in ["option1", "option2", "option3"]:
            value = variant.get(option, "")
            if value and self._is_size(value):
                return self._normalize_size(value)
        
        # Try title
        title = variant.get("title", "")
        if self._is_size(title):
            return self._normalize_size(title)
        
        return None
    
    def _is_size(self, value: str) -> bool:
        """Check if value looks like a size"""
        if not value:
            return False
        
        value = value.strip().upper()
        
        # Numeric sizes (shoe sizes)
        try:
            num = float(re.sub(r'[^0-9.]', '', value))
            if 3 <= num <= 18:
                return True
        except ValueError:
            pass
        
        # Letter sizes
        if value in ["XS", "S", "M", "L", "XL", "XXL", "2XL", "3XL", "OS", "ONE SIZE"]:
            return True
        
        return False
    
    def _normalize_size(self, size: str) -> str:
        """Normalize size string"""
        size = size.strip().upper()
        size = re.sub(r'(US|SIZE|MENS?|WOMENS?)\s*', '', size).strip()
        return size
    
    async def close(self):
        """Close the session"""
        if self._session:
            await self._session.aclose()
            self._session = None


class MultiStoreMonitor:
    """
    Monitors multiple Shopify stores concurrently
    
    Features:
    - Concurrent store monitoring
    - Automatic proxy rotation per store
    - Curated product matching
    - Unified callback system
    - Rate limit coordination
    """
    
    def __init__(self, max_concurrent: int = 10):
        self.max_concurrent = max_concurrent
        self.stores: Dict[str, ShopifyStoreMonitor] = {}
        self._running = False
        self._tasks: List[asyncio.Task] = []
        
        # Callbacks
        self._on_product_found: Optional[Callable[[DetectedProduct], Awaitable[None]]] = None
        
        # Proxy pool
        self._proxies: List[str] = []
        self._proxy_index = 0
        
        logger.info("MultiStoreMonitor initialized", max_concurrent=max_concurrent)
    
    def add_store(
        self,
        name: str,
        url: str,
        delay_ms: int = 3000,
        target_sizes: Optional[List[str]] = None
    ) -> str:
        """Add a store to monitor"""
        store_id = name.lower().replace(" ", "_")
        
        store = MonitoredStore(
            name=name,
            url=url,
            delay_ms=delay_ms
        )
        
        proxy = self._get_next_proxy()
        monitor = ShopifyStoreMonitor(store, target_sizes, proxy)
        
        self.stores[store_id] = monitor
        logger.info("Store added", name=name, url=url)
        
        return store_id
    
    def add_stores_from_list(self, stores: List[Dict]) -> int:
        """Add multiple stores from a list"""
        count = 0
        for store_data in stores:
            self.add_store(
                name=store_data.get("name", ""),
                url=store_data.get("url", ""),
                delay_ms=store_data.get("delay_ms", 3000),
                target_sizes=store_data.get("sizes")
            )
            count += 1
        return count
    
    def set_proxies(self, proxies: List[str]):
        """Set proxy pool"""
        self._proxies = proxies
        logger.info("Proxy pool updated", count=len(proxies))
    
    def _get_next_proxy(self) -> Optional[str]:
        """Get next proxy from pool"""
        if not self._proxies:
            return None
        
        proxy = self._proxies[self._proxy_index % len(self._proxies)]
        self._proxy_index += 1
        return proxy
    
    def set_product_callback(self, callback: Callable[[DetectedProduct], Awaitable[None]]):
        """Set callback for when products are found"""
        self._on_product_found = callback
    
    async def start(self):
        """Start monitoring all stores"""
        if self._running:
            return
        
        self._running = True
        
        # Create tasks for each store
        for store_id, monitor in self.stores.items():
            task = asyncio.create_task(self._monitor_store(store_id, monitor))
            self._tasks.append(task)
        
        logger.info("MultiStoreMonitor started", store_count=len(self.stores))
    
    async def stop(self):
        """Stop all monitoring"""
        self._running = False
        
        # Cancel all tasks
        for task in self._tasks:
            task.cancel()
        
        # Wait for cancellation
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        
        self._tasks.clear()
        
        # Close all sessions
        for monitor in self.stores.values():
            await monitor.close()
        
        logger.info("MultiStoreMonitor stopped")
    
    async def _monitor_store(self, store_id: str, monitor: ShopifyStoreMonitor):
        """Monitor a single store in a loop"""
        while self._running:
            try:
                result = await monitor.check()
                
                if result.success and result.products:
                    for product in result.products:
                        await self._handle_product(monitor.store, product)
                
                # Wait before next check
                await asyncio.sleep(monitor.store.delay_ms / 1000)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Store monitor error", store=store_id, error=str(e))
                await asyncio.sleep(5)
    
    async def _handle_product(self, store: MonitoredStore, product: ProductInfo):
        """Handle a detected product"""
        # Try to match against curated products
        matches = product_db.match_product_title(product.title)
        
        matched_curated = None
        confidence = 0.0
        
        if matches:
            matched_curated, confidence = matches[0]
            logger.info(
                "Product matched curated",
                product=product.title[:40],
                matched=matched_curated.name,
                confidence=f"{confidence:.2f}"
            )
        
        detected = DetectedProduct(
            info=product,
            store=store,
            matched_curated=matched_curated,
            match_confidence=confidence
        )
        
        if self._on_product_found:
            await self._on_product_found(detected)
    
    def get_stats(self) -> Dict:
        """Get monitoring statistics"""
        stats = {
            "running": self._running,
            "store_count": len(self.stores),
            "stores": {}
        }
        
        for store_id, monitor in self.stores.items():
            stats["stores"][store_id] = {
                "name": monitor.store.name,
                "url": monitor.store.url,
                "success_count": monitor.store.success_count,
                "error_count": monitor.store.error_count,
                "products_found": monitor.store.products_found,
                "last_check": monitor.store.last_check.isoformat() if monitor.store.last_check else None,
            }
        
        return stats


# Convenience function to create monitor with default stores
def create_default_monitor(
    target_sizes: Optional[List[str]] = None,
    stores: Optional[List[str]] = None
) -> MultiStoreMonitor:
    """Create a monitor with default Shopify stores"""
    
    DEFAULT_STORES = [
        {"name": "DTLR", "url": "https://www.dtlr.com", "delay_ms": 3000},
        {"name": "Shoe Palace", "url": "https://www.shoepalace.com", "delay_ms": 3000},
        {"name": "Jimmy Jazz", "url": "https://www.jimmyjazz.com", "delay_ms": 3000},
        {"name": "Hibbett", "url": "https://www.hibbett.com", "delay_ms": 3500},
        {"name": "Social Status", "url": "https://www.socialstatuspgh.com", "delay_ms": 4000},
        {"name": "Undefeated", "url": "https://undefeated.com", "delay_ms": 3500},
        {"name": "Concepts", "url": "https://cncpts.com", "delay_ms": 4000},
        {"name": "Bodega", "url": "https://bdgastore.com", "delay_ms": 4000},
        {"name": "Extra Butter", "url": "https://extrabutterny.com", "delay_ms": 4000},
        {"name": "Feature", "url": "https://feature.com", "delay_ms": 4000},
    ]
    
    monitor = MultiStoreMonitor()
    
    # Load curated products
    product_db.load_builtin()
    
    # Filter stores if specified
    if stores:
        stores_lower = [s.lower() for s in stores]
        stores_to_add = [s for s in DEFAULT_STORES if s["name"].lower() in stores_lower]
    else:
        stores_to_add = DEFAULT_STORES
    
    # Add stores with target sizes
    for store_data in stores_to_add:
        monitor.add_store(
            name=store_data["name"],
            url=store_data["url"],
            delay_ms=store_data["delay_ms"],
            target_sizes=target_sizes
        )
    
    return monitor
