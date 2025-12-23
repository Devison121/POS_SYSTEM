from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime

@dataclass
class Store:
    """Store model"""
    id: int
    store_code: str
    name: str
    location: Optional[str] = None

@dataclass
class Product:
    """Product model"""
    id: Optional[int] = None
    product_code: Optional[str] = None
    name: Optional[str] = None
    store_id: Optional[int] = None
    store_code: Optional[str] = None
    sequence_number: Optional[int] = None
    stock_quantity: int = 0
    low_stock_threshold: int = 5
    image: Optional[str] = None
    parent_product_id: Optional[int] = None
    relation_to_parent: Optional[int] = None
    unit: Optional[str] = None
    big_unit: Optional[str] = None

@dataclass
class ProductCosts:
    """Comprehensive product costs and pricing"""
    buying_price: float = 0.0
    retail_price: float = 0.0
    wholesale_price: float = 0.0
    wholesale_threshold: int = 1
    shipping_cost: float = 0.0
    handling_cost: float = 0.0
    landed_cost: float = 0.0
    landed_cost_per_unit: float = 0.0
    retail_profit: float = 0.0
    wholesale_profit: float = 0.0
    expected_margin: float = 0.0
    retail_ratio: float = 0.7
    wholesale_ratio: float = 0.3
    used_actual_data: bool = False

@dataclass
class StockBatch:
    """Stock batch model for FIFO management"""
    id: Optional[int] = None
    product_id: Optional[int] = None
    product_code: Optional[str] = None
    store_id: Optional[int] = None
    store_code: Optional[str] = None
    batch_number: Optional[str] = None
    quantity: int = 0
    buying_price: float = 0.0
    shipping_cost: float = 0.0
    handling_cost: float = 0.0
    expected_margin: float = 0.0
    total_expected_profit: float = 0.0
    received_date: Optional[str] = None
    expiry_date: Optional[str] = None
    is_active: bool = True

@dataclass
class SalesStats:
    """Sales statistics model"""
    total_sales: int = 0
    total_quantity: float = 0.0
    retail_ratio: float = 0.7
    wholesale_ratio: float = 0.3
    retail_revenue: float = 0.0
    wholesale_revenue: float = 0.0

@dataclass
class ValidationResult:
    """Validation result model"""
    is_valid: bool
    value: Any
    message: Optional[str] = None

@dataclass
class UnitStructure:
    """Unit structure for multi-unit products"""
    unit_name: str
    full_name: str
    relation_to_parent: Optional[int] = None
    parent_index: Optional[int] = None
    stock_quantity: int = 0
    retail_price: float = 0.0
    wholesale_price: float = 0.0
    buying_price: float = 0.0

@dataclass
class BatchData:
    """Batch data for multi-unit products"""
    product_id: int
    product_code: str
    product_name: str
    quantity: int
    costs: ProductCosts
    current_stock: int = 0
    relation: int = 1