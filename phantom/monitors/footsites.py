"""
Footsites Monitor
Monitors Foot Locker, Champs, Eastbay, and Footaction
"""

import asyncio
import time
import random
import re
from typing import Optional, List, Dict, Set
from datetime import datetime
from dataclasses import dataclass, field
import httpx
import structlog

from .base import MonitorResult, ProductInfo
from .products import product_db

logger = structlog.get_logger()


@dataclass
class FootsiteProduct:
    """Product from a Footsite"""
    sku: str
    style_id: str
    name: str
    brand: str
    price: float
    image_url: str
    product_url: str
    available_sizes: List[Dict]  # [{size, sku, available}]
    release_date: Optional[datetime] = None


class FootsiteMonitor:
    """
    Monitors Footsite family stores (Foot Locker, Champs, Eastbay, Footaction)
    
    API endpoints:
    - Product search: /api/products/search
    - Product details: /api/products/{sku}
    - Stock check: /api/products/{sku}/stock
    """
    
    SITES = {
        "footlocker": {
            "name": "Foot Locker",
            "base_url": "https://www.footlocker.com",
            "api_base": "https://www.footlocker.com/api",
            "x_api_key": "m38t89Q3dKvBcupKQ6KJm4ByOHNIu2q3",
        },
        "champs": {
            "name": "Champs Sports",
            "base_url": "https://www.champssports.com",
            "api_base": "https://www.champssports.com/api",
            "x_api_key": "m38t89Q3dKvBcupKQ6KJm4ByOHNIu2q3",
        },
        "eastbay": {
            "name": "Eastbay",
            "base_url": "https://www.eastbay.com",
            "api_base": "https://www.eastbay.com/api",
            "x_api_key": "m38t89Q3dKvBcupKQ6KJm4ByOHNIu2q3",
        },
        "footaction": {
            "name": "Footaction",
            "base_url": "https://www.footaction.com",
            "api_base": "https://www.footaction.com/api",
            "x_api_key": "m38t89Q3dKvBcupKQ6KJm4ByOHNIu2q3",
        },
        "kidsfootlocker": {
            "name": "Kids Foot Locker",
            "base_url": "https://www.kidsfootlocker.com",
            "api_base": "https://www.kidsfootlocker.com/api",
            "x_api_key": "m38t89Q3dKvBcupKQ6KJm4ByOHNIu2q3",
        },
    }
    
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    ]
    
    def __init__(
        self,
        site: str = "footlocker",
        keywords: Optional[List[str]] = None,
        target_sizes: Optional[List[str]] = None,
        proxy_url: Optional[str] = None,
        delay_ms: int = 5000
    ):
        if site not in self.SITES:
            raise ValueError(f"Unknown site: {site}. Available: {list(self.SITES.keys())}")
        
        self.site_config = self.SITES[site]
        self.site_name = site
        self.keywords = keywords or []
        self.target_sizes = self._normalize_sizes(target_sizes or [])
        self.proxy_url = proxy_url
        self.delay_ms = delay_ms
        
        # Session
        self._session: Optional[httpx.AsyncClient] = None
        
        # State
        self._seen_products: Dict[str, FootsiteProduct] = {}
        self._seen_skus: Set[str] = set()
        self._last_check: Optional[datetime] = None
        
        # Stats
        self.check_count = 0
        self.products_found = 0
        self.error_count = 0
        
        logger.info("FootsiteMonitor initialized", site=site)
    
    def _normalize_sizes(self, sizes: List[str]) -> List[str]:
        """Normalize size strings"""
        normalized = []
        for size in sizes:
            s = str(size).strip()
            # Remove common prefixes
            s = re.sub(r'^(US|SIZE|M|W)\s*', '', s, flags=re.IGNORECASE).strip()
            normalized.append(s)
        return normalized
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers for Footsite API"""
        return {
            "User-Agent": random.choice(self.USER_AGENTS),
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Content-Type": "application/json",
            "Origin": self.site_config["base_url"],
            "Referer": f"{self.site_config['base_url']}/",
            "x-api-key": self.site_config["x_api_key"],
            "x-fl-request-id": self._generate_request_id(),
        }
    
    def _generate_request_id(self) -> str:
        """Generate a random request ID"""
        import uuid
        return str(uuid.uuid4())
    
    async def _get_session(self) -> httpx.AsyncClient:
        """Get or create HTTP session"""
        if self._session is None or self._session.is_closed:
            proxies = {"all://": self.proxy_url} if self.proxy_url else None
            
            self._session = httpx.AsyncClient(
                timeout=20.0,
                follow_redirects=True,
                proxies=proxies,
                headers=self._get_headers()
            )
        return self._session
    
    async def search_products(self, query: str, page: int = 0, size: int = 60) -> List[Dict]:
        """Search for products"""
        session = await self._get_session()
        
        url = f"{self.site_config['api_base']}/products/search"
        params = {
            "query": query,
            "currentPage": page,
            "pageSize": size,
            "sort": "newArrivals",
        }
        
        try:
            response = await session.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                return data.get("products", [])
            else:
                logger.warning("Search failed", status=response.status_code, site=self.site_name)
                return []
                
        except Exception as e:
            logger.error("Search error", error=str(e), site=self.site_name)
            return []
    
    async def get_product_stock(self, sku: str) -> Optional[Dict]:
        """Get stock info for a product"""
        session = await self._get_session()
        
        url = f"{self.site_config['api_base']}/products/{sku}/stock"
        
        try:
            response = await session.get(url)
            
            if response.status_code == 200:
                return response.json()
            return None
            
        except Exception as e:
            logger.error("Stock check error", sku=sku, error=str(e))
            return None
    
    async def check(self) -> MonitorResult:
        """Perform a single check"""
        start_time = time.time()
        self.check_count += 1
        
        try:
            detected = []
            
            # Search for each keyword
            for keyword in self.keywords:
                products = await self.search_products(keyword)
                
                for product in products:
                    parsed = self._parse_product(product)
                    if parsed and self._is_new_or_restocked(parsed):
                        # Filter by target sizes
                        if self.target_sizes:
                            matching = [s for s in parsed.available_sizes 
                                       if s.get("size") in self.target_sizes]
                            if not matching:
                                continue
                        
                        self._seen_products[parsed.sku] = parsed
                        self._seen_skus.add(parsed.sku)
                        self.products_found += 1
                        
                        # Convert to ProductInfo
                        product_info = self._to_product_info(parsed)
                        detected.append(product_info)
                        
                        logger.info(
                            "Product found",
                            site=self.site_name,
                            name=parsed.name[:50],
                            sku=parsed.sku
                        )
                
                # Small delay between searches
                await asyncio.sleep(0.5)
            
            self._last_check = datetime.now()
            
            return MonitorResult(
                success=True,
                products=detected,
                response_time=time.time() - start_time
            )
            
        except Exception as e:
            self.error_count += 1
            logger.error("Check error", site=self.site_name, error=str(e))
            return MonitorResult(
                success=False,
                error=str(e),
                response_time=time.time() - start_time
            )
    
    def _parse_product(self, data: Dict) -> Optional[FootsiteProduct]:
        """Parse API product data"""
        try:
            sku = data.get("sku", "")
            if not sku:
                return None
            
            # Get available sizes
            available_sizes = []
            sell_able_units = data.get("sellableUnits", [])
            
            for unit in sell_able_units:
                if unit.get("stockLevelStatus") == "inStock":
                    size_info = unit.get("attributes", {})
                    size = size_info.get("size", "")
                    if size:
                        available_sizes.append({
                            "size": size,
                            "sku": unit.get("code", ""),
                            "available": True
                        })
            
            if not available_sizes:
                return None
            
            # Get image
            images = data.get("images", [])
            image_url = ""
            for img in images:
                if img.get("imageType") == "PRIMARY":
                    image_url = img.get("url", "")
                    break
            
            return FootsiteProduct(
                sku=sku,
                style_id=data.get("styleId", ""),
                name=data.get("name", ""),
                brand=data.get("brand", {}).get("name", ""),
                price=float(data.get("price", {}).get("value", 0)),
                image_url=image_url,
                product_url=f"{self.site_config['base_url']}/product/~/{sku}.html",
                available_sizes=available_sizes
            )
            
        except Exception as e:
            logger.warning("Parse error", error=str(e))
            return None
    
    def _is_new_or_restocked(self, product: FootsiteProduct) -> bool:
        """Check if product is new or restocked"""
        if product.sku not in self._seen_skus:
            return True
        
        # Check for new sizes
        old = self._seen_products.get(product.sku)
        if old:
            old_sizes = {s["size"] for s in old.available_sizes}
            new_sizes = {s["size"] for s in product.available_sizes}
            if new_sizes - old_sizes:
                return True
        
        return False
    
    def _to_product_info(self, product: FootsiteProduct) -> ProductInfo:
        """Convert to standard ProductInfo"""
        sizes = [s["size"] for s in product.available_sizes]
        variants = {s["size"]: {"sku": s["sku"]} for s in product.available_sizes}
        
        return ProductInfo(
            url=product.product_url,
            title=product.name,
            sku=product.sku,
            price=product.price,
            image_url=product.image_url,
            available=True,
            sizes_available=sizes,
            variants=variants
        )
    
    async def close(self):
        """Close session"""
        if self._session:
            await self._session.aclose()
            self._session = None


class MultiFootsiteMonitor:
    """
    Monitors multiple Footsite stores concurrently
    """
    
    def __init__(
        self,
        sites: Optional[List[str]] = None,
        keywords: Optional[List[str]] = None,
        target_sizes: Optional[List[str]] = None,
        delay_ms: int = 5000
    ):
        self.sites = sites or ["footlocker", "champs", "eastbay"]
        self.keywords = keywords or []
        self.target_sizes = target_sizes
        self.delay_ms = delay_ms
        
        self.monitors: Dict[str, FootsiteMonitor] = {}
        self._running = False
        self._tasks: List[asyncio.Task] = []
        
        # Callbacks
        self._on_product_found = None
        
        # Initialize monitors
        for site in self.sites:
            self.monitors[site] = FootsiteMonitor(
                site=site,
                keywords=self.keywords,
                target_sizes=self.target_sizes,
                delay_ms=self.delay_ms
            )
        
        logger.info("MultiFootsiteMonitor initialized", sites=self.sites)
    
    def set_keywords(self, keywords: List[str]):
        """Update keywords for all monitors"""
        self.keywords = keywords
        for monitor in self.monitors.values():
            monitor.keywords = keywords
    
    def set_callback(self, callback):
        """Set product found callback"""
        self._on_product_found = callback
    
    async def start(self):
        """Start monitoring"""
        if self._running:
            return
        
        self._running = True
        
        for site, monitor in self.monitors.items():
            task = asyncio.create_task(self._monitor_loop(site, monitor))
            self._tasks.append(task)
        
        logger.info("MultiFootsiteMonitor started")
    
    async def stop(self):
        """Stop monitoring"""
        self._running = False
        
        for task in self._tasks:
            task.cancel()
        
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        
        self._tasks.clear()
        
        for monitor in self.monitors.values():
            await monitor.close()
        
        logger.info("MultiFootsiteMonitor stopped")
    
    async def _monitor_loop(self, site: str, monitor: FootsiteMonitor):
        """Monitor loop for a single site"""
        while self._running:
            try:
                result = await monitor.check()
                
                if result.success and result.products:
                    for product in result.products:
                        if self._on_product_found:
                            await self._on_product_found(site, product)
                
                await asyncio.sleep(self.delay_ms / 1000)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Monitor loop error", site=site, error=str(e))
                await asyncio.sleep(5)
    
    def get_stats(self) -> Dict:
        """Get stats for all monitors"""
        return {
            site: {
                "check_count": m.check_count,
                "products_found": m.products_found,
                "error_count": m.error_count,
                "last_check": m._last_check.isoformat() if m._last_check else None
            }
            for site, m in self.monitors.items()
        }
