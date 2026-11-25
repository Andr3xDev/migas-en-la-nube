from dataclasses import dataclass, field


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
