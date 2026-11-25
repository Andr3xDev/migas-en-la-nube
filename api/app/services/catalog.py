from collections.abc import Iterable
from dataclasses import dataclass

from app.domain.errors import NotFoundError
from app.domain.models import Product, Variant
from app.ports.repositories import ProductRepository

IN_STOCK = "in stock"
MADE_TO_ORDER = "made to order"


@dataclass(frozen=True)
class Availability:
    status: str
    ready_minutes: int | None


def compute_availability(variant: Variant, prep_minutes: int) -> Availability:
    if variant.stock > 0:
        return Availability(IN_STOCK, None)
    return Availability(MADE_TO_ORDER, prep_minutes)


def list_products(repo: ProductRepository) -> list[Product]:
    return repo.list_all()


def get_product(repo: ProductRepository, product_id: str) -> Product:
    product = repo.get(product_id)
    if product is None:
        raise NotFoundError(product_id)
    return product


def seed_products(repo: ProductRepository, items: Iterable[Product]) -> None:
    for item in items:
        if repo.get(item.id) is None:
            repo.create(item)
