"""
Curated Product Database
Pre-configured hyped products with optimized keywords for monitoring
"""

import json
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import structlog

logger = structlog.get_logger()


@dataclass
class CuratedProduct:
    """A curated product with optimized keywords"""
    name: str
    brand: str
    positive_keywords: List[str]
    negative_keywords: List[str]
    optimized_search: str
    retail_price: float
    current_price: float = 0.0
    profit_dollar: float = 0.0
    profit_ratio: float = 0.0
    priority: str = "medium"  # high, medium, low
    sku: Optional[str] = None
    style_code: Optional[str] = None
    release_date: Optional[datetime] = None
    source: str = "manual"
    enabled: bool = True
    
    @property
    def is_profitable(self) -> bool:
        return self.profit_dollar > 20
    
    def matches_title(self, title: str) -> tuple[bool, float]:
        """
        Check if a product title matches this curated product
        Returns (matches: bool, confidence: float 0-1)
        """
        title_lower = title.lower()
        
        # Check negative keywords first (instant reject)
        for neg in self.negative_keywords:
            neg_clean = neg.lstrip('-').lower()
            if neg_clean in title_lower:
                return False, 0.0
        
        # Check positive keywords
        matched_count = 0
        for pos in self.positive_keywords:
            if pos.lower() in title_lower:
                matched_count += 1
        
        if matched_count == 0:
            return False, 0.0
        
        # Confidence based on how many keywords matched
        confidence = min(1.0, matched_count / max(2, len(self.positive_keywords) * 0.5))
        
        # Boost confidence for SKU/style code match
        if self.sku and self.sku.lower() in title_lower:
            confidence = min(1.0, confidence + 0.3)
        if self.style_code and self.style_code.lower() in title_lower:
            confidence = min(1.0, confidence + 0.3)
        
        return True, confidence
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "brand": self.brand,
            "positive_keywords": self.positive_keywords,
            "negative_keywords": self.negative_keywords,
            "optimized_search": self.optimized_search,
            "retail_price": self.retail_price,
            "current_price": self.current_price,
            "profit_dollar": self.profit_dollar,
            "profit_ratio": self.profit_ratio,
            "priority": self.priority,
            "sku": self.sku,
            "enabled": self.enabled,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CuratedProduct':
        return cls(
            name=data.get("name", ""),
            brand=data.get("brand", ""),
            positive_keywords=data.get("positive_keywords", []),
            negative_keywords=data.get("negative_keywords", []),
            optimized_search=data.get("optimized_search", ""),
            retail_price=data.get("retail_price", 0),
            current_price=data.get("current_price", 0),
            profit_dollar=data.get("profit_dollar", 0),
            profit_ratio=data.get("profit_ratio", 0),
            priority=data.get("priority", "medium"),
            sku=data.get("sku"),
            style_code=data.get("style_code"),
            source=data.get("source", "imported"),
            enabled=data.get("enabled", True),
        )


class ProductDatabase:
    """
    Database of curated products to monitor
    Loads from JSON files and provides fast keyword matching
    """
    
    def __init__(self):
        self.products: Dict[str, CuratedProduct] = {}
        self._by_brand: Dict[str, List[str]] = {}
        self._by_priority: Dict[str, List[str]] = {}
        logger.info("ProductDatabase initialized")
    
    def add_product(self, product: CuratedProduct) -> str:
        """Add a product to the database"""
        # Generate ID from name
        product_id = product.name.lower().replace(" ", "_").replace("-", "_")[:50]
        
        # Ensure unique ID
        base_id = product_id
        counter = 1
        while product_id in self.products:
            product_id = f"{base_id}_{counter}"
            counter += 1
        
        self.products[product_id] = product
        
        # Index by brand
        brand = product.brand.lower()
        if brand not in self._by_brand:
            self._by_brand[brand] = []
        self._by_brand[brand].append(product_id)
        
        # Index by priority
        if product.priority not in self._by_priority:
            self._by_priority[product.priority] = []
        self._by_priority[product.priority].append(product_id)
        
        return product_id
    
    def load_from_json(self, json_path: str) -> int:
        """Load products from a JSON file"""
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
            
            products_data = data.get("keywords_by_shoe", [])
            
            count = 0
            for item in products_data:
                product = CuratedProduct.from_dict(item)
                self.add_product(product)
                count += 1
            
            logger.info("Products loaded from JSON", path=json_path, count=count)
            return count
            
        except Exception as e:
            logger.error("Failed to load products", path=json_path, error=str(e))
            return 0
    
    def load_builtin(self):
        """Load built-in curated products"""
        builtin_products = [
            CuratedProduct(
                name="Off-White x Nike Dunk Low Pine Green",
                brand="nike",
                positive_keywords=["ow dunk pine green", "off white dunk", "virgil dunk", "off white pine green"],
                negative_keywords=["-kids", "-gs", "-ps", "-td", "-infant", "-toddler", "-preschool", "-gradeschool"],
                optimized_search="off white dunk ow dunk pine green -kids -gs -ps -td -infant -toddler",
                retail_price=100,
                current_price=800,
                profit_dollar=700,
                profit_ratio=8.0,
                priority="high",
            ),
            CuratedProduct(
                name="Fragment x Jordan 1 High",
                brand="jordan",
                positive_keywords=["fragment jordan 1", "fragment aj1", "frag jordan", "fragment design jordan"],
                negative_keywords=["-kids", "-gs", "-ps", "-td", "-infant", "-toddler", "-preschool", "-gradeschool"],
                optimized_search="fragment jordan 1 fragment aj1 frag jordan -kids -gs -ps -td",
                retail_price=170,
                current_price=1200,
                profit_dollar=1030,
                profit_ratio=7.06,
                priority="high",
            ),
            CuratedProduct(
                name="Travis Scott Jordan 1 Low Mocha",
                brand="jordan",
                positive_keywords=["travis mocha", "cactus jack mocha", "travis scott jordan 1 low", "ts jordan 1 mocha"],
                negative_keywords=["-kids", "-gs", "-ps", "-td", "-infant", "-toddler", "-preschool", "-gradeschool"],
                optimized_search="travis scott jordan 1 low ts jordan 1 mocha travis mocha -kids -gs",
                retail_price=150,
                current_price=650,
                profit_dollar=500,
                profit_ratio=4.33,
                priority="high",
            ),
            CuratedProduct(
                name="Jordan 4 Retro Black Cat",
                brand="jordan",
                positive_keywords=["jordan 4 black cat", "aj4 black", "black cat 4", "jordan iv black cat"],
                negative_keywords=["-kids", "-gs", "-ps", "-td", "-infant", "-toddler", "-preschool", "-gradeschool"],
                optimized_search="jordan 4 black cat aj4 black jordan iv black cat -kids -gs -ps",
                retail_price=130,
                current_price=280,
                profit_dollar=150,
                profit_ratio=2.15,
                priority="high",
            ),
            CuratedProduct(
                name="Jordan 1 Retro High Chicago Lost and Found",
                brand="jordan",
                positive_keywords=["aj1 chicago", "chicago lost found", "chicago 1s", "jordan 1 chicago"],
                negative_keywords=["-kids", "-gs", "-ps", "-td", "-infant", "-toddler", "-preschool", "-gradeschool"],
                optimized_search="jordan 1 chicago aj1 chicago chicago lost found -kids -gs -ps",
                retail_price=170,
                current_price=350,
                profit_dollar=180,
                profit_ratio=2.06,
                priority="high",
            ),
            CuratedProduct(
                name="Nike Dunk Low Panda",
                brand="nike",
                positive_keywords=["dunk low panda", "panda dunk", "black white dunk", "dunk panda"],
                negative_keywords=["-kids", "-gs", "-ps", "-td", "-infant", "-toddler", "-preschool", "-gradeschool"],
                optimized_search="dunk low panda panda dunk black white dunk -kids -gs -ps -td",
                retail_price=100,
                current_price=180,
                profit_dollar=80,
                profit_ratio=1.8,
                priority="medium",
            ),
            CuratedProduct(
                name="Jordan 11 Retro Bred",
                brand="jordan",
                positive_keywords=["bred 11", "aj11 bred", "jordan 11 bred", "jordan xi bred"],
                negative_keywords=["-kids", "-gs", "-ps", "-td", "-infant", "-toddler", "-preschool", "-gradeschool"],
                optimized_search="jordan 11 bred aj11 bred bred 11 -kids -gs -ps -td",
                retail_price=220,
                current_price=420,
                profit_dollar=200,
                profit_ratio=1.91,
                priority="medium",
            ),
            CuratedProduct(
                name="New Balance 550 White Grey",
                brand="new balance",
                positive_keywords=["nb 550", "new balance 550", "550 white grey", "nb550"],
                negative_keywords=["-kids", "-gs", "-ps", "-td", "-infant", "-toddler", "-preschool", "-gradeschool"],
                optimized_search="new balance 550 nb 550 550 white grey -kids -gs -ps",
                retail_price=110,
                current_price=180,
                profit_dollar=70,
                profit_ratio=1.64,
                priority="medium",
            ),
            CuratedProduct(
                name="Yeezy Boost 350 V2 Onyx",
                brand="yeezy",
                positive_keywords=["yeezy 350 onyx", "yeezy onyx", "350 v2 onyx", "boost 350 onyx"],
                negative_keywords=["-kids", "-gs", "-ps", "-td", "-infant", "-toddler", "-preschool", "-gradeschool"],
                optimized_search="yeezy 350 onyx yeezy onyx 350 v2 onyx -kids -gs -ps",
                retail_price=230,
                current_price=280,
                profit_dollar=50,
                profit_ratio=1.22,
                priority="medium",
            ),
            CuratedProduct(
                name="Jordan 4 Retro Military Blue",
                brand="jordan",
                positive_keywords=["jordan 4 military blue", "aj4 military", "military blue 4", "jordan iv military"],
                negative_keywords=["-kids", "-gs", "-ps", "-td", "-infant", "-toddler", "-preschool", "-gradeschool"],
                optimized_search="jordan 4 military blue aj4 military military blue 4 -kids -gs",
                retail_price=200,
                current_price=300,
                profit_dollar=100,
                profit_ratio=1.5,
                priority="medium",
            ),
        ]
        
        for product in builtin_products:
            self.add_product(product)
        
        logger.info("Built-in products loaded", count=len(builtin_products))
    
    def get_product(self, product_id: str) -> Optional[CuratedProduct]:
        """Get product by ID"""
        return self.products.get(product_id)
    
    def get_by_brand(self, brand: str) -> List[CuratedProduct]:
        """Get all products for a brand"""
        ids = self._by_brand.get(brand.lower(), [])
        return [self.products[pid] for pid in ids if pid in self.products]
    
    def get_by_priority(self, priority: str) -> List[CuratedProduct]:
        """Get all products by priority"""
        ids = self._by_priority.get(priority, [])
        return [self.products[pid] for pid in ids if pid in self.products]
    
    def get_high_priority(self) -> List[CuratedProduct]:
        """Get all high priority products"""
        return self.get_by_priority("high")
    
    def get_enabled(self) -> List[CuratedProduct]:
        """Get all enabled products"""
        return [p for p in self.products.values() if p.enabled]
    
    def get_profitable(self, min_profit: float = 50) -> List[CuratedProduct]:
        """Get products with minimum profit threshold"""
        return [p for p in self.products.values() if p.profit_dollar >= min_profit]
    
    def match_product_title(self, title: str) -> List[tuple[CuratedProduct, float]]:
        """
        Match a product title against all curated products
        Returns list of (product, confidence) tuples, sorted by confidence
        """
        matches = []
        
        for product in self.products.values():
            if not product.enabled:
                continue
            
            matched, confidence = product.matches_title(title)
            if matched:
                matches.append((product, confidence))
        
        # Sort by confidence descending
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches
    
    def get_all_keywords(self) -> str:
        """Get combined optimized search for all enabled products"""
        keywords = []
        for product in self.get_enabled():
            keywords.append(product.optimized_search)
        return " | ".join(keywords)
    
    def export_to_json(self, path: str):
        """Export database to JSON"""
        data = {
            "generated_at": datetime.now().isoformat(),
            "total_products": len(self.products),
            "keywords_by_shoe": [p.to_dict() for p in self.products.values()]
        }
        
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info("Products exported", path=path, count=len(self.products))
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        return {
            "total": len(self.products),
            "enabled": len(self.get_enabled()),
            "high_priority": len(self.get_high_priority()),
            "profitable": len(self.get_profitable()),
            "by_brand": {brand: len(ids) for brand, ids in self._by_brand.items()},
        }


# Global product database
product_db = ProductDatabase()
