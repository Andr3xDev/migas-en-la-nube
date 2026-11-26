from datetime import datetime, timedelta, timezone

import pytest

from app.adapters.memory.orders import MemoryOrderRepository
from app.adapters.memory.products import MemoryProductRepository
from app.adapters.memory.users import MemoryUserRepository
from app.domain.errors import ConcurrencyConflictError, NotFoundError
from app.domain.models import Order, OrderItem, Product, User, Variant
from app.services import accounts

SHOP_TZ = timezone(timedelta(hours=-5))
ANA = "ana@example.com"
BETO = "beto@example.com"


def make_product(product_id: str) -> Product:
    return Product(product_id, product_id.title(), "bakery", "d", None, 30, [Variant("S", 100, 9)])


@pytest.fixture
def products():
    repo = MemoryProductRepository()
    for product_id in ("p1", "p2", "p3", "p4"):
        repo.create(make_product(product_id))
    return repo


@pytest.fixture
def users():
    repo = MemoryUserRepository()
    repo.create(User("ana-id", ANA, "hash"))
    repo.create(User("beto-id", BETO, "hash"))
    return repo


@pytest.fixture
def orders():
    return MemoryOrderRepository()


def place(orders, code, user_id, lines, hour=10, status="received"):
    orders.create(
        Order(
            id=code,
            customer_name="n",
            phone="3001234567",
            pickup_time=datetime(2026, 6, 10, hour, tzinfo=SHOP_TZ),
            pickup_date="2026-06-10",
            items=[OrderItem(pid, pid, "S", 100, qty) for pid, qty in lines],
            total=0,
            status=status,
            user_id=user_id,
        )
    )


def ids(items):
    return [item.id for item in items]


def test_list_user_orders_returns_only_own_newest_first_including_cancelled(orders):
    place(orders, "A-OLD", "ana-id", [("p1", 1)], hour=8)
    place(orders, "A-NEW", "ana-id", [("p1", 1)], hour=15, status="cancelled")
    place(orders, "B-ONE", "beto-id", [("p1", 1)])
    place(orders, "GUEST", None, [("p1", 1)])

    assert ids(accounts.list_user_orders(orders, "ana-id")) == ["A-NEW", "A-OLD"]


def test_list_user_orders_without_history_returns_empty(orders):
    assert accounts.list_user_orders(orders, "ana-id") == []


def test_remove_favorite_drops_it_and_absent_one_is_ok(users, products):
    accounts.add_favorite(users, products, ANA, "p1")
    accounts.add_favorite(users, products, ANA, "p2")

    accounts.remove_favorite(users, ANA, "p1")
    accounts.remove_favorite(users, ANA, "p3")

    assert accounts.list_favorites(users, ANA) == ["p2"]


def test_add_unknown_product_raises_not_found_and_keeps_list(users, products):
    accounts.add_favorite(users, products, ANA, "p1")

    with pytest.raises(NotFoundError):
        accounts.add_favorite(users, products, ANA, "ghost")

    assert accounts.list_favorites(users, ANA) == ["p1"]


def test_favorites_are_isolated_between_users(users, products):
    accounts.add_favorite(users, products, ANA, "p1")

    assert accounts.list_favorites(users, BETO) == []


def test_add_favorite_retries_after_concurrent_user_update(users, products):
    real_replace = users.replace
    failures = []

    def flaky_replace(user):
        if not failures:
            failures.append(user.id)
            raise ConcurrencyConflictError(user.id)
        return real_replace(user)

    users.replace = flaky_replace

    accounts.add_favorite(users, products, ANA, "p1")

    assert accounts.list_favorites(users, ANA) == ["p1"]


def test_top_products_ranks_by_total_quantity_across_orders(orders, products):
    place(orders, "O1", "ana-id", [("p1", 3), ("p2", 3), ("p3", 2)])
    place(orders, "O2", "ana-id", [("p1", 2), ("p4", 1)])

    assert ids(accounts.top_products(orders, products, "ana-id")) == ["p1", "p2", "p3"]


def test_top_products_ignores_cancelled_orders(orders, products):
    place(orders, "O1", "ana-id", [("p1", 1)])
    place(orders, "O2", "ana-id", [("p2", 9)], status="cancelled")

    assert ids(accounts.top_products(orders, products, "ana-id")) == ["p1"]


def test_top_products_breaks_ties_by_product_id_ascending(orders, products):
    place(orders, "O1", "ana-id", [("p3", 2), ("p1", 2), ("p2", 2), ("p4", 2)])

    assert ids(accounts.top_products(orders, products, "ana-id")) == ["p1", "p2", "p3"]


def test_top_products_skips_deleted_products(orders, products):
    place(orders, "O1", "ana-id", [("p1", 5), ("p2", 3)])
    products.delete("p1")

    assert ids(accounts.top_products(orders, products, "ana-id")) == ["p2"]


def test_top_products_counts_only_own_orders(orders, products):
    place(orders, "O1", "beto-id", [("p1", 5)])

    assert accounts.top_products(orders, products, "ana-id") == []
