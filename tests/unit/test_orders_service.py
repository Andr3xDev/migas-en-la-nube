from datetime import datetime, timedelta, timezone

import pytest

from app.adapters.memory.orders import MemoryOrderRepository
from app.adapters.memory.products import MemoryProductRepository
from app.domain.errors import ConflictError, RuleViolationError
from app.domain.models import Product, Variant
from app.services import orders as orders_service
from app.services.orders import CODE_ALPHABET, NewOrder, NewOrderItem, create_order

SHOP_TZ = timezone(timedelta(hours=-5))
DAY = "2026-06-10"


def local(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 6, 10, hour, minute, tzinfo=SHOP_TZ)


def make_product(product_id: str = "croissant", stock: int = 5, prep: int = 90) -> Product:
    return Product(
        product_id,
        "Croissant",
        "bakery",
        "Buttery",
        None,
        prep,
        [Variant("Single", 6000, stock)],
    )


def order_for(pickup: datetime, *items: tuple[str, str, int]) -> NewOrder:
    return NewOrder(
        customer_name="Ana",
        phone="3001234567",
        pickup_time=pickup,
        items=[NewOrderItem(*item) for item in items],
    )


@pytest.fixture
def products():
    return MemoryProductRepository()


@pytest.fixture
def orders():
    return MemoryOrderRepository()


NOON = local(12)


def place(products, orders, order: NewOrder, now: datetime = NOON):
    return create_order(products, orders, order, now=now)


def stock_of(products, product_id: str = "croissant") -> int:
    return products.get(product_id).variants[0].stock


def test_shop_timezone_is_fixed_utc_minus_5():
    assert orders_service.SHOP_TIMEZONE.utcoffset(None) == timedelta(hours=-5)


def test_create_order_stores_received_order_with_code_total_and_partition(products, orders):
    products.create(make_product(stock=5))

    order = place(products, orders, order_for(local(12, 10), ("croissant", "Single", 2)))

    assert order.status == "received"
    assert len(order.id) == 8 and set(order.id) <= set(CODE_ALPHABET)
    assert order.pickup_date == DAY
    assert order.total == 12000
    assert order.items[0].unit_price == 6000
    assert orders.get(order.id, DAY) is not None


def test_create_order_with_duplicate_items_aggregates_quantity(products, orders):
    products.create(make_product(stock=5))

    order = place(
        products,
        orders,
        order_for(local(12, 10), ("croissant", "Single", 1), ("croissant", "Single", 2)),
    )

    assert [(i.quantity) for i in order.items] == [3]
    assert stock_of(products) == 2


@pytest.mark.parametrize("product_id, variant", [("missing", "Single"), ("croissant", "Huge")])
def test_create_order_with_unknown_product_or_variant_raises_rule_violation(
    products, orders, product_id, variant
):
    products.create(make_product())

    with pytest.raises(RuleViolationError):
        place(products, orders, order_for(local(12, 10), (product_id, variant, 1)))
    assert orders.list_by_date(DAY) == []


def test_create_order_at_closing_time_is_accepted(products, orders):
    products.create(make_product())

    place(products, orders, order_for(local(20, 0), ("croissant", "Single", 1)), now=local(4))


@pytest.mark.parametrize("pickup", [local(5, 59), local(20, 1)])
def test_create_order_outside_business_hours_raises_rule_violation(products, orders, pickup):
    products.create(make_product())

    with pytest.raises(RuleViolationError):
        place(products, orders, order_for(pickup, ("croissant", "Single", 1)), now=local(4))
    assert orders.list_by_date(DAY) == []


def test_create_order_with_pickup_in_the_past_raises_rule_violation(products, orders):
    products.create(make_product())

    with pytest.raises(RuleViolationError):
        place(products, orders, order_for(local(11), ("croissant", "Single", 1)))


def test_create_order_made_to_order_before_prep_time_is_rejected_and_stock_unchanged(
    products, orders
):
    products.create(make_product(stock=0, prep=90))

    with pytest.raises(RuleViolationError):
        place(products, orders, order_for(local(12, 30), ("croissant", "Single", 1)))
    assert stock_of(products) == 0 and orders.list_by_date(DAY) == []


def test_create_order_made_to_order_after_prep_time_is_accepted(products, orders):
    products.create(make_product(stock=0, prep=90))

    place(products, orders, order_for(local(13, 30), ("croissant", "Single", 1)))


def test_create_order_decrements_in_stock_variant_and_records_it(products, orders):
    products.create(make_product(stock=5))

    order = place(products, orders, order_for(local(12, 10), ("croissant", "Single", 2)))

    assert stock_of(products) == 3
    assert [(d.product_id, d.variant_name, d.quantity) for d in order.stock_decrements] == [
        ("croissant", "Single", 2)
    ]


def test_create_order_made_to_order_item_leaves_stock_and_records_no_decrement(products, orders):
    products.create(make_product(stock=1))

    order = place(products, orders, order_for(local(14), ("croissant", "Single", 3)))

    assert stock_of(products) == 1 and order.stock_decrements == []


def test_create_order_when_conflict_then_success_decrements_once(products, orders):
    products.create(make_product(stock=5))
    bumps = []

    def bump_once(product_id):
        if not bumps:
            bumps.append(product_id)
            products.bump_etag(product_id)

    products.before_replace = bump_once

    place(products, orders, order_for(local(12, 10), ("croissant", "Single", 1)))

    assert stock_of(products) == 4


def test_create_order_last_unit_race_accepts_both_and_stock_stays_zero(products, orders):
    products.create(make_product(stock=1))
    request = order_for(local(14), ("croissant", "Single", 1))
    inner_orders = []

    def competing_order(product_id):
        products.before_replace = None
        inner_orders.append(place(products, orders, request))

    products.before_replace = competing_order

    outer = place(products, orders, request)

    assert inner_orders and outer
    assert stock_of(products) == 0
    assert len(orders.list_by_date(DAY)) == 2


def test_create_order_when_retries_exhausted_raises_conflict_and_stores_nothing(products, orders):
    products.create(make_product(stock=5))
    products.before_replace = products.bump_etag

    with pytest.raises(ConflictError):
        place(products, orders, order_for(local(12, 10), ("croissant", "Single", 1)))
    assert stock_of(products) == 5 and orders.list_by_date(DAY) == []


def test_create_order_when_later_product_fails_restores_earlier_product(products, orders):
    products.create(make_product("a", stock=5))
    products.create(make_product("b", stock=5))
    products.before_replace = lambda product_id: (
        products.bump_etag(product_id) if product_id == "b" else None
    )

    with pytest.raises(ConflictError):
        place(
            products,
            orders,
            order_for(local(12, 10), ("b", "Single", 1), ("a", "Single", 2)),
        )

    assert stock_of(products, "a") == 5 and stock_of(products, "b") == 5
    assert orders.list_by_date(DAY) == []


def test_create_order_when_a_restore_fails_still_restores_the_rest_and_raises_original(
    products, orders
):
    for product_id in ("a", "b", "c"):
        products.create(make_product(product_id, stock=5))
    state = {"c_failed": False}

    def before_replace(product_id: str) -> None:
        if product_id == "c":
            state["c_failed"] = True
            raise RuntimeError("original")
        if product_id == "a" and state["c_failed"]:
            products.bump_etag("a")

    products.before_replace = before_replace

    with pytest.raises(RuntimeError, match="original") as raised:
        place(
            products,
            orders,
            order_for(
                local(12, 10),
                ("a", "Single", 1),
                ("b", "Single", 1),
                ("c", "Single", 1),
            ),
        )

    assert stock_of(products, "b") == 5
    assert stock_of(products, "a") == 4
    assert any("Stock restore failed" in note for note in raised.value.__notes__)
    assert orders.list_by_date(DAY) == []


def test_create_order_retries_with_new_code_when_code_collides(products, orders, monkeypatch):
    products.create(make_product(stock=5))
    codes = iter(["TAKEN000", "FRESH000"])
    monkeypatch.setattr(orders_service, "generate_code", lambda: next(codes))
    real_create = orders.create

    def conflict_on_first_code(order):
        if order.id == "TAKEN000":
            raise ConflictError(order.id)
        return real_create(order)

    monkeypatch.setattr(orders, "create", conflict_on_first_code)

    order = place(products, orders, order_for(local(12, 10), ("croissant", "Single", 1)))

    assert order.id == "FRESH000"
    assert stock_of(products) == 4
