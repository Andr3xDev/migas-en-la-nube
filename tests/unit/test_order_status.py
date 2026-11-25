from datetime import datetime, timedelta, timezone

import pytest

from app.adapters.memory.orders import MemoryOrderRepository
from app.adapters.memory.products import MemoryProductRepository
from app.domain.errors import ConflictError, NotFoundError, RuleViolationError
from app.domain.models import Order, OrderItem, Product, StockDecrement, Variant
from app.services import orders as orders_service

SHOP_TZ = timezone(timedelta(hours=-5))
DAY = "2026-06-10"


@pytest.fixture
def products():
    repo = MemoryProductRepository()
    repo.create(
        Product("croissant", "Croissant", "bakery", "d", None, 90, [Variant("Single", 6000, 3)])
    )
    return repo


@pytest.fixture
def orders():
    return MemoryOrderRepository()


def add_order(
    orders,
    order_id: str = "ABCD2345",
    status: str = "received",
    decrements: list[StockDecrement] | None = None,
    hour: int = 12,
    pickup_date: str = DAY,
) -> Order:
    return orders.create(
        Order(
            id=order_id,
            customer_name="Ana",
            phone="300",
            pickup_time=datetime(2026, 6, 10, hour, tzinfo=SHOP_TZ),
            pickup_date=pickup_date,
            items=[OrderItem("croissant", "Croissant", "Single", 6000, 2)],
            total=12000,
            status=status,
            stock_decrements=decrements or [],
        )
    )


def change(orders, products, status: str, order_id: str = "ABCD2345", date: str = DAY) -> Order:
    return orders_service.change_status(orders, products, order_id, date, status)


def stock(products) -> int:
    return products.get("croissant").variants[0].stock


def test_list_by_date_returns_only_that_day_earliest_pickup_first(orders):
    add_order(orders, "LATE0000", hour=15)
    add_order(orders, "EARLY000", hour=9)
    add_order(orders, "OTHERDAY", pickup_date="2026-06-11")

    assert [o.id for o in orders_service.list_by_date(orders, DAY)] == ["EARLY000", "LATE0000"]


@pytest.mark.parametrize(
    ("current", "target"),
    [
        ("received", "preparing"),
        ("preparing", "ready"),
        ("ready", "delivered"),
        ("received", "cancelled"),
        ("preparing", "cancelled"),
        ("ready", "cancelled"),
    ],
)
def test_change_status_allows_next_step_and_cancel(orders, products, current, target):
    add_order(orders, status=current)

    result = change(orders, products, target)

    assert result.status == target
    assert orders.get("ABCD2345", DAY).status == target


@pytest.mark.parametrize(
    ("current", "target"),
    [
        ("received", "ready"),
        ("received", "delivered"),
        ("received", "received"),
        ("ready", "preparing"),
        ("delivered", "cancelled"),
        ("delivered", "preparing"),
        ("cancelled", "cancelled"),
        ("cancelled", "received"),
    ],
)
def test_change_status_with_invalid_transition_raises_conflict_and_keeps_status(
    orders, products, current, target
):
    add_order(orders, status=current)

    with pytest.raises(ConflictError):
        change(orders, products, target)

    assert orders.get("ABCD2345", DAY).status == current


def test_change_status_with_unknown_status_raises_rule_violation(orders, products):
    add_order(orders)

    with pytest.raises(RuleViolationError):
        change(orders, products, "teleported")


@pytest.mark.parametrize(("order_id", "date"), [("NOPE0000", DAY), ("ABCD2345", "2026-06-11")])
def test_change_status_with_unknown_order_or_wrong_date_raises_not_found(
    orders, products, order_id, date
):
    add_order(orders)

    with pytest.raises(NotFoundError):
        change(orders, products, "preparing", order_id=order_id, date=date)


def test_cancel_restores_decremented_stock(orders, products):
    add_order(orders, decrements=[StockDecrement("croissant", "Single", 2)])

    change(orders, products, "cancelled")

    assert stock(products) == 5


def test_cancel_with_made_to_order_item_leaves_stock_unchanged(orders, products):
    add_order(orders, decrements=[])

    change(orders, products, "cancelled")

    assert stock(products) == 3


def test_second_cancel_raises_conflict_and_does_not_restore_twice(orders, products):
    add_order(orders, decrements=[StockDecrement("croissant", "Single", 2)])
    change(orders, products, "cancelled")

    with pytest.raises(ConflictError):
        change(orders, products, "cancelled")

    assert stock(products) == 5


def test_cancel_skips_deleted_product_and_variant_but_restores_the_rest(orders, products):
    add_order(
        orders,
        decrements=[
            StockDecrement("deleted-product", "Single", 1),
            StockDecrement("croissant", "Deleted variant", 1),
            StockDecrement("croissant", "Single", 2),
        ],
    )

    result = change(orders, products, "cancelled")

    assert result.status == "cancelled"
    assert stock(products) == 5


def test_cancel_retries_restore_after_a_stock_write_conflict(orders, products):
    add_order(orders, decrements=[StockDecrement("croissant", "Single", 2)])
    raced = []

    def race_once(product_id: str) -> None:
        if not raced:
            raced.append(product_id)
            products.bump_etag(product_id)

    products.before_replace = race_once

    change(orders, products, "cancelled")

    assert stock(products) == 5
