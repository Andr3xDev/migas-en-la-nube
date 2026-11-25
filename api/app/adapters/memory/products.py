from collections.abc import Callable
from copy import deepcopy
from uuid import uuid4

from app.domain.errors import ConcurrencyConflictError, NotFoundError
from app.domain.models import Product


class MemoryProductRepository:
    def __init__(self) -> None:
        self._products: dict[str, Product] = {}
        # Test seam: lets a test interleave a competing write before the etag check.
        self.before_replace: Callable[[str], None] | None = None

    def bump_etag(self, product_id: str) -> None:
        self._products[product_id].etag = uuid4().hex

    def list_all(self) -> list[Product]:
        return [deepcopy(product) for product in self._products.values()]

    def get(self, product_id: str) -> Product | None:
        product = self._products.get(product_id)
        return deepcopy(product) if product else None

    def create(self, product: Product) -> Product:
        stored = deepcopy(product)
        stored.etag = uuid4().hex
        self._products[stored.id] = stored
        return deepcopy(stored)

    def replace(self, product: Product) -> Product:
        if self.before_replace is not None:
            self.before_replace(product.id)
        current = self._products.get(product.id)
        if current is None:
            raise NotFoundError(product.id)
        if current.etag != product.etag:
            raise ConcurrencyConflictError(product.id)
        return self.create(product)

    # The id is the key, so a category change needs no relocation here.
    move = replace

    def delete(self, product_id: str) -> None:
        if self._products.pop(product_id, None) is None:
            raise NotFoundError(product_id)
