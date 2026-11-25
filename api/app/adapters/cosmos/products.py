from typing import Any

from azure.core import MatchConditions
from azure.cosmos.container import ContainerProxy
from azure.cosmos.exceptions import (
    CosmosAccessConditionFailedError,
    CosmosResourceExistsError,
    CosmosResourceNotFoundError,
)

from app.domain.errors import ConcurrencyConflictError, ConflictError, NotFoundError
from app.domain.models import Product, Variant

CONTAINER_NAME = "products"


def to_document(product: Product) -> dict[str, Any]:
    return {
        "id": product.id,
        "name": product.name,
        "category": product.category,
        "description": product.description,
        "imageUrl": product.image_url,
        "prepMinutes": product.prep_minutes,
        "variants": [
            {"name": v.name, "price": v.price, "stock": v.stock} for v in product.variants
        ],
    }


def from_document(document: dict[str, Any]) -> Product:
    return Product(
        id=document["id"],
        name=document["name"],
        category=document["category"],
        description=document["description"],
        image_url=document.get("imageUrl"),
        prep_minutes=document["prepMinutes"],
        variants=[Variant(**variant) for variant in document["variants"]],
        etag=document["_etag"],
    )


class CosmosProductRepository:
    def __init__(self, container: ContainerProxy) -> None:
        self._container = container

    def list_all(self) -> list[Product]:
        documents = self._container.query_items(
            "SELECT * FROM c", enable_cross_partition_query=True
        )
        return [from_document(document) for document in documents]

    def get(self, product_id: str) -> Product | None:
        documents = self._container.query_items(
            "SELECT * FROM c WHERE c.id = @id",
            parameters=[{"name": "@id", "value": product_id}],
            enable_cross_partition_query=True,
        )
        return next((from_document(document) for document in documents), None)

    def create(self, product: Product) -> Product:
        # Partitioned by /category: Cosmos only rejects duplicates within a partition.
        if self.get(product.id) is not None:
            raise ConflictError(product.id)
        return self._create_in_partition(product)

    def _create_in_partition(self, product: Product) -> Product:
        try:
            created = self._container.create_item(to_document(product))
        except CosmosResourceExistsError as error:
            raise ConflictError(product.id) from error
        return from_document(created)

    def replace(self, product: Product) -> Product:
        try:
            replaced = self._container.replace_item(
                product.id,
                to_document(product),
                etag=product.etag,
                match_condition=MatchConditions.IfNotModified,
            )
        except CosmosAccessConditionFailedError as error:
            raise ConcurrencyConflictError(product.id) from error
        return from_document(replaced)

    def move(self, product: Product) -> Product:
        """Change the partition key: create in the new category, then delete the old copy."""
        current = self.get(product.id)
        if current is None:
            raise NotFoundError(product.id)
        if current.etag != product.etag:
            raise ConcurrencyConflictError(product.id)
        if current.category == product.category:
            return self.replace(product)
        # The etag check above and the copy are not atomic; a concurrent write in between is lost.
        created = self._create_in_partition(product)
        try:
            self._container.delete_item(current.id, partition_key=current.category)
        except Exception as error:
            self._container.delete_item(created.id, partition_key=created.category)
            if isinstance(error, CosmosResourceNotFoundError):
                raise NotFoundError(product.id) from error
            raise
        return created

    def delete(self, product_id: str) -> None:
        current = self.get(product_id)
        if current is None:
            raise NotFoundError(product_id)
        try:
            self._container.delete_item(product_id, partition_key=current.category)
        except CosmosResourceNotFoundError as error:
            raise NotFoundError(product_id) from error
