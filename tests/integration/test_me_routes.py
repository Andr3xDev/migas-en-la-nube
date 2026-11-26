from datetime import datetime, timedelta, timezone

import pytest

from app.domain.models import Order, OrderItem

SHOP_TZ = timezone(timedelta(hours=-5))
ME_ROUTES = [
    ("GET", "/api/me/orders"),
    ("GET", "/api/me/favorites"),
    ("PUT", "/api/me/favorites/croissant"),
    ("DELETE", "/api/me/favorites/croissant"),
    ("GET", "/api/me/top-products"),
]


def make_order(code, user_id) -> Order:
    return Order(
        id=code,
        customer_name="n",
        phone="3001234567",
        pickup_time=datetime(2026, 6, 10, 10, tzinfo=SHOP_TZ),
        pickup_date="2026-06-10",
        items=[OrderItem("croissant", "Croissant", "Single", 6000, 1)],
        total=6000,
        user_id=user_id,
    )


@pytest.mark.parametrize(("method", "url"), ME_ROUTES)
def test_me_route_without_token_returns_401(client, stack, method, url):
    assert client.request(method, url).status_code == 401


def test_orders_lists_only_callers_orders_in_order_response_shape(client, stack):
    ana = stack.headers_for("ana@example.com")
    ana_id = stack.users.get_by_email("ana@example.com").id
    for code, user_id in [("ANA00001", ana_id), ("OTHER001", "someone-else"), ("GUEST001", None)]:
        stack.orders.create(make_order(code, user_id))

    response = client.get("/api/me/orders", headers=ana)

    assert response.status_code == 200
    assert [o["code"] for o in response.json()] == ["ANA00001"]
    assert {"status", "items", "total", "pickupTime"} <= response.json()[0].keys()


def test_favorites_add_is_idempotent_and_remove_clears_it(client, stack):
    ana = stack.headers_for("ana@example.com")

    assert client.put("/api/me/favorites/croissant", headers=ana).status_code == 204
    assert client.put("/api/me/favorites/croissant", headers=ana).status_code == 204
    assert client.get("/api/me/favorites", headers=ana).json() == ["croissant"]
    assert client.delete("/api/me/favorites/croissant", headers=ana).status_code == 204
    assert client.delete("/api/me/favorites/croissant", headers=ana).status_code == 204
    assert client.get("/api/me/favorites", headers=ana).json() == []


def test_favorite_unknown_product_returns_404_and_list_unchanged(client, stack):
    ana = stack.headers_for("ana@example.com")

    assert client.put("/api/me/favorites/ghost", headers=ana).status_code == 404
    assert client.get("/api/me/favorites", headers=ana).json() == []


def test_top_products_returns_products_in_product_shape(client, stack):
    ana = stack.headers_for("ana@example.com")
    ana_id = stack.users.get_by_email("ana@example.com").id
    stack.orders.create(make_order("CROI0001", ana_id))

    response = client.get("/api/me/top-products", headers=ana)

    assert response.status_code == 200
    body = response.json()
    assert [p["id"] for p in body] == ["croissant"]
    assert body[0].keys() == {
        "id",
        "name",
        "category",
        "description",
        "imageUrl",
        "prepMinutes",
        "etag",
        "variants",
    }
