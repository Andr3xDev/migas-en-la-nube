from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Variant:
    name: str
    price: int
    stock: int


@dataclass
class Product:
    id: str
    name: str
    category: str
    description: str
    image_url: str | None
    prep_minutes: int
    variants: list[Variant] = field(default_factory=list)
    etag: str | None = None


@dataclass
class OrderItem:
    product_id: str
    product_name: str
    variant_name: str
    unit_price: int
    quantity: int


@dataclass
class StockDecrement:
    product_id: str
    variant_name: str
    quantity: int


@dataclass
class Order:
    id: str
    customer_name: str
    phone: str
    pickup_time: datetime
    pickup_date: str
    items: list[OrderItem]
    total: int
    status: str = "received"
    user_id: str | None = None
    stock_decrements: list[StockDecrement] = field(default_factory=list)
    etag: str | None = None
