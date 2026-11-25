from datetime import datetime, timedelta, timezone

import pytest

KEY = "route-test-signing-key-32-bytes-min"
PASSWORD = "correct horse"
SHOP_TZ = timezone(timedelta(hours=-5))
ME_ROUTES = [
    ("GET", "/api/me/orders"),
    ("GET", "/api/me/favorites"),
    ("PUT", "/api/me/favorites/croissant"),
    ("DELETE", "/api/me/favorites/croissant"),
    ("GET", "/api/me/top-products"),
]


@pytest.fixture
def stack(client):
    # Imported after `client` so both come from the same app.* module instances.
    from app.adapters.local_auth import LocalAuthProvider
    from app.adapters.memory.orders import MemoryOrderRepository
    from app.adapters.memory.products import MemoryProductRepository
    from app.adapters.memory.users import MemoryUserRepository
    from app.api.deps import (
        get_auth_provider,
        get_order_repository,
        get_product_repository,
        get_user_repository,
    )
    from app.domain.models import Product, Variant

    users = MemoryUserRepository()
    orders = MemoryOrderRepository()
    products = MemoryProductRepository()
    products.create(
        Product("croissant", "Croissant", "bakery", "d", None, 90, [Variant("Single", 6000, 5)])
    )
    auth = LocalAuthProvider(users, KEY, login_failure_delay_seconds=0, sleep=lambda _: None)
    overrides = client.app.dependency_overrides
    overrides[get_user_repository] = lambda: users
    overrides[get_auth_provider] = lambda: auth
    overrides[get_order_repository] = lambda: orders
    overrides[get_product_repository] = lambda: products
    return auth, orders


def headers_for(auth, email: str) -> dict[str, str]:
    auth.register(email, PASSWORD)
    return {"X-Pdc-Token": f"Bearer {auth.login(email, PASSWORD)}"}


@pytest.mark.parametrize(("method", "url"), ME_ROUTES)
def test_me_route_without_token_returns_401(client, stack, method, url):
    assert client.request(method, url).status_code == 401


def test_orders_lists_only_callers_orders_in_order_response_shape(client, stack):
    from app.domain.models import Order, OrderItem

    auth, orders = stack
    ana = headers_for(auth, "ana@example.com")
    ana_id = auth.verify_token(ana["X-Pdc-Token"].split()[1]).user_id
    for code, user_id in [("ANA00001", ana_id), ("OTHER001", "someone-else"), ("GUEST001", None)]:
        orders.create(
            Order(
                id=code,
                customer_name="n",
                phone="3",
                pickup_time=datetime(2026, 6, 10, 10, tzinfo=SHOP_TZ),
                pickup_date="2026-06-10",
                items=[OrderItem("croissant", "Croissant", "Single", 6000, 1)],
                total=6000,
                user_id=user_id,
            )
        )

    response = client.get("/api/me/orders", headers=ana)

    assert response.status_code == 200
    assert [o["code"] for o in response.json()] == ["ANA00001"]
    assert {"status", "items", "total", "pickupTime"} <= response.json()[0].keys()


def test_favorites_add_is_idempotent_and_remove_clears_it(client, stack):
    ana = headers_for(stack[0], "ana@example.com")

    assert client.put("/api/me/favorites/croissant", headers=ana).status_code == 204
    assert client.put("/api/me/favorites/croissant", headers=ana).status_code == 204
    assert client.get("/api/me/favorites", headers=ana).json() == ["croissant"]
    assert client.delete("/api/me/favorites/croissant", headers=ana).status_code == 204
    assert client.delete("/api/me/favorites/croissant", headers=ana).status_code == 204
    assert client.get("/api/me/favorites", headers=ana).json() == []


def test_favorite_unknown_product_returns_404_and_list_unchanged(client, stack):
    ana = headers_for(stack[0], "ana@example.com")

    assert client.put("/api/me/favorites/ghost", headers=ana).status_code == 404
    assert client.get("/api/me/favorites", headers=ana).json() == []


def test_favorites_are_isolated_between_users(client, stack):
    auth = stack[0]
    ana = headers_for(auth, "ana@example.com")
    beto = headers_for(auth, "beto@example.com")
    client.put("/api/me/favorites/croissant", headers=ana)

    assert client.get("/api/me/favorites", headers=beto).json() == []


def test_top_products_with_no_orders_returns_empty_list(client, stack):
    ana = headers_for(stack[0], "ana@example.com")

    response = client.get("/api/me/top-products", headers=ana)

    assert response.status_code == 200
    assert response.json() == []
