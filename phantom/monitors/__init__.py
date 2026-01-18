"""Product monitoring modules"""

from .base import BaseMonitor, MonitorResult, ProductInfo, MonitorConfig
from .keywords import KeywordMatcher
from .products import CuratedProduct, ProductDatabase, product_db
from .sites import Site, SiteType, SHOPIFY_STORES, FOOTSITE_STORES, get_site
from .shopify_monitor import ShopifyStoreMonitor, MultiStoreMonitor, DetectedProduct, create_default_monitor
from .footsites import FootsiteMonitor, MultiFootsiteMonitor
from .manager import MonitorManager, MonitorEvent, monitor_manager, quick_start_monitors

__all__ = [
    # Base
    'BaseMonitor', 'MonitorResult', 'ProductInfo', 'MonitorConfig',
    'KeywordMatcher',
    
    # Products
    'CuratedProduct', 'ProductDatabase', 'product_db',
    
    # Sites
    'Site', 'SiteType', 'SHOPIFY_STORES', 'FOOTSITE_STORES', 'get_site',
    
    # Shopify
    'ShopifyStoreMonitor', 'MultiStoreMonitor', 'DetectedProduct', 'create_default_monitor',
    
    # Footsites
    'FootsiteMonitor', 'MultiFootsiteMonitor',
    
    # Manager
    'MonitorManager', 'MonitorEvent', 'monitor_manager', 'quick_start_monitors',
]
