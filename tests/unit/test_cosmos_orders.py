from datetime import datetime, timedelta, timezone

import pytest
from azure.cosmos.exceptions import CosmosAccessConditionFailedError, CosmosResourceNotFoundError

from app.adapters.cosmos.orders import CosmosOrderRepository, to_document
from app.domain.errors import ConcurrencyConflictError
from app.domain.models import Order, OrderItem, StockDecrement

ORDER = Order(
    id="ABC123",
    customer_name="Ana",
    phone="3001234567",
    pickup_time=datetime(2026, 6, 10, 9, 30, tzinfo=timezone(timedelta(hours=-5))),
    pickup_date="2026-06-10",
    items=[OrderItem("p1", "Croissant", "Single", 6000, 2)],
    total=12000,
    stock_decrements=[StockDecrement("p1", "Single", 2)],
    etag="e1",
)


class FakeContainer:
    def read_item(self, item, partition_key):
        raise CosmosResourceNotFoundError(status_code=404, message="missing")

    def create_item(self, body):
        return {**body, "_etag": "e1", "_rid": "r", "_ts": 1}

    def replace_item(self, *args, **kwargs):
        raise CosmosAccessConditionFailedError(status_code=412, message="stale")


class QueryContainer:
    def __init__(self):
        self.calls = []

    def query_items(self, query, **kwargs):
        self.calls.append((query, kwargs))
        return []


def test_list_before_runs_capped_cross_partition_query_newest_first():
    container = QueryContainer()

    CosmosOrderRepository(container).list_before("2026-06-10", 5)

    query, kwargs = container.calls[0]
    assert "c.pickupDate < @date ORDER BY c.pickupTime DESC" in query and "TOP @limit" in query
    assert {"name": "@limit", "value": 5} in kwargs["parameters"]
    assert kwargs["enable_cross_partition_query"] is True


def test_list_from_runs_cross_partition_query_earliest_first():
    container = QueryContainer()

    CosmosOrderRepository(container).list_from("2026-06-10")

    query, kwargs = container.calls[0]
    assert "c.pickupDate >= @date ORDER BY c.pickupTime" in query
    assert kwargs["enable_cross_partition_query"] is True


def test_get_returns_none_when_missing():
    assert CosmosOrderRepository(FakeContainer()).get("ABC123", "2026-06-10") is None


def test_replace_maps_412_to_concurrency_conflict():
    with pytest.raises(ConcurrencyConflictError):
        CosmosOrderRepository(FakeContainer()).replace(ORDER)


def test_document_round_trip_keeps_offset_and_decrements():
    document = to_document(ORDER)
    assert document["stockDecrements"] == [
        {"productId": "p1", "variantName": "Single", "quantity": 2}
    ]
    assert document["pickupTime"] == "2026-06-10T09:30:00-05:00"
    assert CosmosOrderRepository(FakeContainer()).create(ORDER) == ORDER
