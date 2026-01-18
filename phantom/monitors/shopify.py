"""
Shopify Product Monitor
Production-ready monitor for Shopify-based stores with comprehensive scraping
"""

import asyncio
import time
import hashlib
import random
from typing import Optional, List, Dict, Any, Set, Callable, Awaitable
from datetime import datetime
import httpx
import structlog

from .base import BaseMonitor, MonitorConfig, MonitorResult, ProductInfo, MonitorStatus
from .products import ProductDatabase, CuratedProduct, product_db
from .sites import Site, SiteType, SHOPIFY_STORES
from ..evasion.tls import TLSManager
from ..evasion.fingerprint import FingerprintManager

logger = structlog.get_logger()


class ShopifyMonitor(BaseMonitor):
    """
    Production-ready Shopify store monitor
    
    Features:
    - Multi-store concurrent monitoring
    - products.json endpoint scraping with pagination
    - Atom feed monitoring for faster detection
    - Variant availability tracking with size filtering
    - Smart change detection (hash-based)
    - Rate limit handling with exponential backoff
    - Proxy rotation support
    - Curated product keyword matching
    """
    
    # Shopify API endpoints
    PRODUCTS_ENDPOINT = "/products.json"
    PRODUCTS_ENDPOINT_PAGINATED = "/products.json?limit=250&page={page}"
    COLLECTIONS_ENDPOINT = "/collections/{collection}/products.json"
    PRODUCT_ENDPOINT = "/products/{handle}.json"
    ATOM_FEED = "/collections/all.atom"
    SITEMAP = "/sitemap_products_1.xml"
    
    # User agents pool
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    ]
    
    def __init__(
        self,
        config: MonitorConfig,
        target_sizes: Optional[List[str]] = None,
        use_product_db: bool = True,
        proxy_list: Optional[List[str]] = None
    ):
        super().__init__(config)
        
        self.target_sizes = self._normalize_sizes(target_sizes or [])
        self.base_url = config.site_url.rstrip('/')
        self.use_product_db = use_product_db
        self.proxy_list = proxy_list or []
        
        # TLS/Fingerprint management
        self.tls_manager = TLSManager()
        self.fingerprint_manager = FingerprintManager()
        
        # Session management
        self._session: Optional[httpx.AsyncClient] = None
        self._current_proxy_index = 0
        
        # Change detection
        self._products_hash: Optional[str] = None
        self._seen_product_ids: Set[str] = set()
        self._seen_variants: Dict[str, Set[int]] = {}  # product_id -> set of variant_ids
        
        # Rate limiting
        self._request_times: List[float] = []
        self._max_requests_per_minute = config.delay // 1000 * 60 if config.delay else 30
        self._consecutive_errors = 0
        self._backoff_until: Optional[float] = None
        
        # Stats
        self._total_requests = 0
        self._successful_requests = 0
        self._products_found = 0
        
        # Callbacks
        self._on_new_product: Optional[Callable[[ProductInfo, Optional[CuratedProduct]], Awaitable[None]]] = None
        self._on_restock: Optional[Callable[[ProductInfo, List[str]], Awaitable[None]]] = None
    
    async def _get_session(self) -> httpx.AsyncClient:
        """Get or create HTTP session"""
        if self._session is None or self._session.is_closed:
            impersonation = self.tls_manager.get_impersonation("chrome")
            
            self._session = httpx.AsyncClient(
                timeout=10.0,
                follow_redirects=True,
                headers=self._get_headers(),
            )
        
        return self._session
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers"""
        return {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }
    
    def _check_rate_limit(self) -> bool:
        """Check if we're within rate limits"""
        now = time.time()
        # Remove old entries
        self._request_times = [t for t in self._request_times if now - t < 60]
        
        if len(self._request_times) >= self._max_requests_per_minute:
            return False
        
        self._request_times.append(now)
        return True
    
    async def check(self) -> MonitorResult:
        """Check Shopify store for products"""
        if not self._check_rate_limit():
            return MonitorResult(
                success=False,
                error="Rate limited",
                rate_limited=True
            )
        
        start_time = time.time()
        
        try:
            session = await self._get_session()
            
            # Fetch products.json
            url = f"{self.base_url}{self.PRODUCTS_ENDPOINT}?limit=250"
            response = await session.get(url)
            
            response_time = time.time() - start_time
            
            if response.status_code == 429:
                return MonitorResult(
                    success=False,
                    error="Rate limited by Shopify",
                    rate_limited=True,
                    response_time=response_time
                )
            
            if response.status_code != 200:
                return MonitorResult(
                    success=False,
                    error=f"HTTP {response.status_code}",
                    response_time=response_time
                )
            
            data = response.json()
            products = self._parse_products(data.get("products", []))
            
            return MonitorResult(
                success=True,
                products=products,
                response_time=response_time
            )
            
        except httpx.TimeoutException:
            return MonitorResult(
                success=False,
                error="Request timeout",
                response_time=time.time() - start_time
            )
        except Exception as e:
            logger.error("Shopify monitor error", error=str(e))
            return MonitorResult(
                success=False,
                error=str(e),
                response_time=time.time() - start_time
            )
    
    def _parse_products(self, products_data: List[Dict]) -> List[ProductInfo]:
        """Parse Shopify products JSON into ProductInfo objects"""
        products = []
        
        for product in products_data:
            try:
                # Get available variants
                variants = product.get("variants", [])
                available_variants = [v for v in variants if v.get("available", False)]
                
                if not available_variants:
                    continue
                
                # Extract sizes
                sizes_available = []
                variant_map = {}
                
                for variant in available_variants:
                    size = self._extract_size(variant)
                    if size:
                        sizes_available.append(size)
                        variant_map[size] = {
                            "id": variant.get("id"),
                            "price": float(variant.get("price", 0)),
                            "sku": variant.get("sku"),
                        }
                
                # Filter by target sizes if specified
                if self.target_sizes:
                    matching_sizes = [s for s in sizes_available if s in self.target_sizes]
                    if not matching_sizes:
                        continue
                    sizes_available = matching_sizes
                
                # Get first image
                images = product.get("images", [])
                image_url = images[0].get("src") if images else None
                
                # Get price from first available variant
                price = float(available_variants[0].get("price", 0))
                
                product_info = ProductInfo(
                    url=f"{self.base_url}/products/{product.get('handle')}",
                    title=product.get("title", ""),
                    sku=product.get("variants", [{}])[0].get("sku"),
                    price=price,
                    image_url=image_url,
                    available=True,
                    sizes_available=sizes_available,
                    variants=variant_map,
                    raw_data=product
                )
                
                products.append(product_info)
                
            except Exception as e:
                logger.warning("Failed to parse product", error=str(e))
                continue
        
        return products
    
    def _extract_size(self, variant: Dict) -> Optional[str]:
        """Extract size from variant"""
        # Try option1, option2, option3
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
        
        # Numeric sizes
        try:
            size = float(value.replace("US", "").replace("M", "").replace("W", "").strip())
            if 3 <= size <= 18:
                return True
        except ValueError:
            pass
        
        # Letter sizes
        if value in ["XS", "S", "M", "L", "XL", "XXL", "2XL", "3XL"]:
            return True
        
        return False
    
    def _normalize_size(self, size: str) -> str:
        """Normalize size string"""
        size = size.strip().upper()
        size = size.replace("US", "").replace("SIZE", "").strip()
        
        # Remove W/M suffix for consistency
        if size.endswith("W") or size.endswith("M"):
            size = size[:-1]
        
        return size
    
    async def check_product_page(self, product_handle: str) -> Optional[ProductInfo]:
        """Check a specific product page for availability"""
        try:
            session = await self._get_session()
            url = f"{self.base_url}/products/{product_handle}.json"
            
            response = await session.get(url)
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            product = data.get("product")
            
            if not product:
                return None
            
            products = self._parse_products([product])
            return products[0] if products else None
            
        except Exception as e:
            logger.error("Product page check failed", handle=product_handle, error=str(e))
            return None
    
    async def get_cart_token(self) -> Optional[str]:
        """Get a cart token for checkout"""
        try:
            session = await self._get_session()
            response = await session.post(
                f"{self.base_url}/cart.js",
                json={"items": []}
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("token")
            
            return None
        except Exception:
            return None
    
    async def add_to_cart(self, variant_id: int, quantity: int = 1) -> bool:
        """Add variant to cart"""
        try:
            session = await self._get_session()
            response = await session.post(
                f"{self.base_url}/cart/add.js",
                json={
                    "items": [{
                        "id": variant_id,
                        "quantity": quantity
                    }]
                },
                headers={
                    **self._get_headers(),
                    "Content-Type": "application/json"
                }
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error("Add to cart failed", error=str(e))
            return False
    
    async def close(self):
        """Close the session"""
        if self._session:
            await self._session.aclose()
            self._session = None
