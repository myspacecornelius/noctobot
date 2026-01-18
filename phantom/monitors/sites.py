"""
Site Definitions and Store Database
Contains known Shopify sites, Footsites, and other monitored stores
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum


class SiteType(Enum):
    SHOPIFY = "shopify"
    FOOTSITE = "footsite"
    SNKRS = "snkrs"
    CONFIRMED = "confirmed"
    YEEZY_SUPPLY = "yeezy_supply"
    SUPREME = "supreme"
    CUSTOM = "custom"


@dataclass
class Site:
    """Site configuration"""
    name: str
    url: str
    site_type: SiteType
    region: str = "US"
    
    # API endpoints
    products_endpoint: str = "/products.json"
    collections_endpoint: str = "/collections/{collection}/products.json"
    stock_endpoint: Optional[str] = None
    
    # Site-specific settings
    requires_auth: bool = False
    api_key: Optional[str] = None
    rate_limit: int = 30  # requests per minute
    
    # Checkout info
    checkout_type: str = "standard"
    supports_paypal: bool = True
    
    # Proxy requirements
    requires_residential: bool = False
    
    keywords: List[str] = field(default_factory=list)  # Site-specific keywords


# ============ SHOPIFY STORES ============

SHOPIFY_STORES: Dict[str, Site] = {
    # Tier 1 - High traffic, good stock
    "dtlr": Site(
        name="DTLR",
        url="https://www.dtlr.com",
        site_type=SiteType.SHOPIFY,
        rate_limit=20,
    ),
    "shoe_palace": Site(
        name="Shoe Palace",
        url="https://www.shoepalace.com",
        site_type=SiteType.SHOPIFY,
        rate_limit=25,
    ),
    "jimmy_jazz": Site(
        name="Jimmy Jazz",
        url="https://www.jimmyjazz.com",
        site_type=SiteType.SHOPIFY,
        rate_limit=25,
    ),
    "hibbett": Site(
        name="Hibbett",
        url="https://www.hibbett.com",
        site_type=SiteType.SHOPIFY,
        rate_limit=20,
    ),
    "city_gear": Site(
        name="City Gear",
        url="https://www.citygear.com",
        site_type=SiteType.SHOPIFY,
        rate_limit=30,
    ),
    
    # Tier 2 - Boutiques
    "social_status": Site(
        name="Social Status",
        url="https://www.socialstatuspgh.com",
        site_type=SiteType.SHOPIFY,
        rate_limit=30,
    ),
    "undefeated": Site(
        name="Undefeated",
        url="https://undefeated.com",
        site_type=SiteType.SHOPIFY,
        rate_limit=25,
    ),
    "concepts": Site(
        name="Concepts",
        url="https://cncpts.com",
        site_type=SiteType.SHOPIFY,
        rate_limit=25,
    ),
    "bodega": Site(
        name="Bodega",
        url="https://bdgastore.com",
        site_type=SiteType.SHOPIFY,
        rate_limit=30,
    ),
    "kith": Site(
        name="Kith",
        url="https://kith.com",
        site_type=SiteType.SHOPIFY,
        rate_limit=20,
        requires_residential=True,
    ),
    "a_ma_maniere": Site(
        name="A Ma Maniére",
        url="https://www.a-]ma-maniere.com",
        site_type=SiteType.SHOPIFY,
        rate_limit=25,
    ),
    "notre": Site(
        name="Notre",
        url="https://www.notre-shop.com",
        site_type=SiteType.SHOPIFY,
        rate_limit=30,
    ),
    "extra_butter": Site(
        name="Extra Butter",
        url="https://extrabutterny.com",
        site_type=SiteType.SHOPIFY,
        rate_limit=30,
    ),
    "lapstone_hammer": Site(
        name="Lapstone & Hammer",
        url="https://www.lapstoneandhammer.com",
        site_type=SiteType.SHOPIFY,
        rate_limit=30,
    ),
    "feature": Site(
        name="Feature",
        url="https://feature.com",
        site_type=SiteType.SHOPIFY,
        rate_limit=30,
    ),
    "bait": Site(
        name="BAIT",
        url="https://www.baitme.com",
        site_type=SiteType.SHOPIFY,
        rate_limit=25,
    ),
    
    # Tier 3 - Regional/Smaller
    "sneaker_politics": Site(
        name="Sneaker Politics",
        url="https://sneakerpolitics.com",
        site_type=SiteType.SHOPIFY,
        rate_limit=30,
    ),
    "xhibition": Site(
        name="Xhibition",
        url="https://www.xhibition.co",
        site_type=SiteType.SHOPIFY,
        rate_limit=30,
    ),
    "sole_fly": Site(
        name="SoleFly",
        url="https://www.solefly.com",
        site_type=SiteType.SHOPIFY,
        rate_limit=30,
    ),
    "unknwn": Site(
        name="UNKNWN",
        url="https://www.unknwn.com",
        site_type=SiteType.SHOPIFY,
        rate_limit=30,
    ),
    "oneness": Site(
        name="Oneness",
        url="https://www.onenessboutique.com",
        site_type=SiteType.SHOPIFY,
        rate_limit=35,
    ),
    "wish_atl": Site(
        name="Wish ATL",
        url="https://wishatl.com",
        site_type=SiteType.SHOPIFY,
        rate_limit=35,
    ),
    "among_equals": Site(
        name="Among Equals",
        url="https://amongequals.com",
        site_type=SiteType.SHOPIFY,
        rate_limit=35,
    ),
}


# ============ FOOTSITES ============

FOOTSITE_STORES: Dict[str, Site] = {
    "footlocker_us": Site(
        name="Foot Locker US",
        url="https://www.footlocker.com",
        site_type=SiteType.FOOTSITE,
        region="US",
        products_endpoint="/api/products/search",
        stock_endpoint="/api/products/{sku}/availability",
        rate_limit=15,
        requires_residential=True,
    ),
    "footlocker_ca": Site(
        name="Foot Locker CA",
        url="https://www.footlocker.ca",
        site_type=SiteType.FOOTSITE,
        region="CA",
        rate_limit=15,
        requires_residential=True,
    ),
    "champs": Site(
        name="Champs Sports",
        url="https://www.champssports.com",
        site_type=SiteType.FOOTSITE,
        region="US",
        rate_limit=15,
        requires_residential=True,
    ),
    "eastbay": Site(
        name="Eastbay",
        url="https://www.eastbay.com",
        site_type=SiteType.FOOTSITE,
        region="US",
        rate_limit=15,
        requires_residential=True,
    ),
    "footaction": Site(
        name="Footaction",
        url="https://www.footaction.com",
        site_type=SiteType.FOOTSITE,
        region="US",
        rate_limit=15,
        requires_residential=True,
    ),
    "kids_footlocker": Site(
        name="Kids Foot Locker",
        url="https://www.kidsfootlocker.com",
        site_type=SiteType.FOOTSITE,
        region="US",
        rate_limit=15,
    ),
}


# ============ NIKE ============

NIKE_STORES: Dict[str, Site] = {
    "snkrs_us": Site(
        name="SNKRS US",
        url="https://www.nike.com",
        site_type=SiteType.SNKRS,
        region="US",
        products_endpoint="/api/discover/product_feed/threads",
        rate_limit=10,
        requires_residential=True,
    ),
    "nike_us": Site(
        name="Nike.com US",
        url="https://www.nike.com",
        site_type=SiteType.SNKRS,
        region="US",
        rate_limit=15,
    ),
}


# ============ ADIDAS ============

ADIDAS_STORES: Dict[str, Site] = {
    "confirmed_us": Site(
        name="Confirmed US",
        url="https://www.adidas.com",
        site_type=SiteType.CONFIRMED,
        region="US",
        rate_limit=10,
        requires_residential=True,
    ),
    "yeezy_supply": Site(
        name="Yeezy Supply",
        url="https://www.yeezysupply.com",
        site_type=SiteType.YEEZY_SUPPLY,
        rate_limit=15,
        requires_residential=True,
    ),
}


# ============ ALL SITES ============

ALL_SITES: Dict[str, Site] = {
    **SHOPIFY_STORES,
    **FOOTSITE_STORES,
    **NIKE_STORES,
    **ADIDAS_STORES,
}


def get_site(site_id: str) -> Optional[Site]:
    """Get site by ID"""
    return ALL_SITES.get(site_id.lower().replace(" ", "_").replace("-", "_"))


def get_sites_by_type(site_type: SiteType) -> List[Site]:
    """Get all sites of a specific type"""
    return [s for s in ALL_SITES.values() if s.site_type == site_type]


def get_shopify_sites() -> List[Site]:
    """Get all Shopify sites"""
    return list(SHOPIFY_STORES.values())


def get_footsites() -> List[Site]:
    """Get all Footsites"""
    return list(FOOTSITE_STORES.values())
