from datetime import datetime
from typing import Any

from azure.core import MatchConditions
from azure.cosmos.container import ContainerProxy
from azure.cosmos.exceptions import (
    CosmosAccessConditionFailedError,
    CosmosResourceExistsError,
    CosmosResourceNotFoundError,
)

from app.domain.errors import ConcurrencyConflictError, ConflictError, NotFoundError
from app.domain.models import Order, OrderItem, StockDecrement

CONTAINER_NAME = "orders"


def to_document(order: Order) -> dict[str, Any]:
    return {
        "id": order.id,
        "customerName": order.customer_name,
        "phone": order.phone,
        "pickupTime": order.pickup_time.isoformat(),
        "pickupDate": order.pickup_date,
        "items": [
            {
                "productId": i.product_id,
                "productName": i.product_name,
                "variantName": i.variant_name,
                "unitPrice": i.unit_price,
                "quantity": i.quantity,
            }
            for i in order.items
        ],
        "total": order.total,
        "status": order.status,
        "userId": order.user_id,
        "stockDecrements": [
            {"productId": d.product_id, "variantName": d.variant_name, "quantity": d.quantity}
            for d in order.stock_decrements
        ],
    }


def from_document(document: dict[str, Any]) -> Order:
    return Order(
        id=document["id"],
        customer_name=document["customerName"],
        phone=document["phone"],
        pickup_time=datetime.fromisoformat(document["pickupTime"]),
        pickup_date=document["pickupDate"],
        items=[
            OrderItem(
                product_id=i["productId"],
                product_name=i["productName"],
                variant_name=i["variantName"],
                unit_price=i["unitPrice"],
                quantity=i["quantity"],
            )
            for i in document["items"]
        ],
        total=document["total"],
        status=document["status"],
        user_id=document.get("userId"),
        stock_decrements=[
            StockDecrement(d["productId"], d["variantName"], d["quantity"])
            for d in document.get("stockDecrements", [])
        ],
        etag=document["_etag"],
    )


class CosmosOrderRepository:
    def __init__(self, container: ContainerProxy) -> None:
        self._container = container

    def create(self, order: Order) -> Order:
        try:
            created = self._container.create_item(to_document(order))
        except CosmosResourceExistsError as error:
            raise ConflictError(order.id) from error
        return from_document(created)

    def get(self, order_id: str, pickup_date: str) -> Order | None:
        try:
            document = self._container.read_item(order_id, partition_key=pickup_date)
        except CosmosResourceNotFoundError:
            return None
        return from_document(document)

    def replace(self, order: Order) -> Order:
        try:
            replaced = self._container.replace_item(
                order.id,
                to_document(order),
                etag=order.etag,
                match_condition=MatchConditions.IfNotModified,
            )
        except CosmosAccessConditionFailedError as error:
            raise ConcurrencyConflictError(order.id) from error
        except CosmosResourceNotFoundError as error:
            raise NotFoundError(order.id) from error
        return from_document(replaced)

    def list_by_date(self, pickup_date: str) -> list[Order]:
        documents = self._container.query_items(
            "SELECT * FROM c WHERE c.pickupDate = @date ORDER BY c.pickupTime",
            parameters=[{"name": "@date", "value": pickup_date}],
            partition_key=pickup_date,
        )
        return [from_document(document) for document in documents]

    def list_by_user(self, user_id: str) -> list[Order]:
        documents = self._container.query_items(
            "SELECT * FROM c WHERE c.userId = @userId",
            parameters=[{"name": "@userId", "value": user_id}],
            enable_cross_partition_query=True,
        )
        return [from_document(document) for document in documents]
