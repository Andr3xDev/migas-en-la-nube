from datetime import datetime, timedelta, timezone

import pytest

from app.adapters.memory.orders import MemoryOrderRepository
from app.domain.errors import ConcurrencyConflictError, ConflictError
from app.domain.models import Order, OrderItem

SHOP_TZ = timezone(timedelta(hours=-5))


def make_order(order_id: str, hour: int = 10, status: str = "received") -> Order:
    return Order(
        id=order_id,
        customer_name="Ana",
        phone="3001234567",
        pickup_time=datetime(2026, 6, 10, hour, 0, tzinfo=SHOP_TZ),
        status=status,
        pickup_date="2026-06-10",
        items=[OrderItem("croissant", "Croissant", "Single", 6000, 1)],
        total=6000,
        user_id="u1" if order_id == "MINE" else None,
    )


def test_get_with_wrong_pickup_date_returns_none():
    repo = MemoryOrderRepository()
    repo.create(make_order("AAAA2222"))

    assert repo.get("AAAA2222", "2026-06-11") is None


def test_create_with_existing_id_raises_conflict_error():
    repo = MemoryOrderRepository()
    repo.create(make_order("AAAA2222"))

    with pytest.raises(ConflictError):
        repo.create(make_order("AAAA2222"))


def test_replace_with_stale_etag_raises_concurrency_conflict():
    repo = MemoryOrderRepository()
    repo.create(make_order("AAAA2222"))
    first = repo.get("AAAA2222", "2026-06-10")
    second = repo.get("AAAA2222", "2026-06-10")
    repo.replace(first)

    with pytest.raises(ConcurrencyConflictError):
        repo.replace(second)


def test_list_by_user_returns_only_that_users_orders():
    repo = MemoryOrderRepository()
    repo.create(make_order("MINE"))
    repo.create(make_order("OTHER222"))

    assert [o.id for o in repo.list_by_user("u1")] == ["MINE"]
