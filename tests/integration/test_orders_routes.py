from datetime import datetime, timedelta, timezone

import pytest

from app.api.deps import get_now
from app.domain.models import ADMIN_ROLE

SHOP_TZ = timezone(timedelta(hours=-5))
NOW = datetime(2026, 6, 10, 12, 0, tzinfo=SHOP_TZ)
PICKUP = "2026-06-10T13:00:00-05:00"


@pytest.fixture
def stack(stack, client):
    client.app.dependency_overrides[get_now] = lambda: NOW
    return stack


def body(**changes):
    payload = {
        "customerName": "Ana",
        "phone": "3001234567",
        "pickupTime": PICKUP,
        "items": [{"productId": "croissant", "variantName": "Single", "quantity": 2}],
    }
    return {**payload, **changes}


def test_post_order_as_guest_returns_201_with_code_and_total(client, stack):
    response = client.post("/api/orders", json=body())

    assert response.status_code == 201
    data = response.json()
    assert len(data["code"]) == 8 and data["status"] == "received"
    assert data["total"] == 12000
    assert data["items"] == [
        {
            "productId": "croissant",
            "productName": "Croissant",
            "variantName": "Single",
            "unitPrice": 6000,
            "quantity": 2,
        }
    ]
    assert datetime.fromisoformat(data["pickupTime"]) == datetime.fromisoformat(PICKUP)


@pytest.mark.parametrize(
    "payload",
    [
        {"customerName": None},
        {"phone": "   "},
        {"items": []},
        {"items": [{"productId": "croissant", "variantName": "Single", "quantity": 0}]},
        {"items": [{"productId": "missing", "variantName": "Single", "quantity": 1}]},
        {"items": [{"productId": "croissant", "variantName": "Single", "quantity": 51}]},
        {"items": [{"productId": "croissant", "variantName": "Single", "quantity": 1}] * 21},
        {"customerName": "x" * 101},
        {"phone": "1" * 31},
        {"pickupTime": "2026-06-10T13:00:00"},
    ],
    ids=[
        "missing name",
        "blank phone",
        "no items",
        "zero quantity",
        "unknown product",
        "quantity over max",
        "too many items",
        "name too long",
        "phone too long",
        "pickup without offset",
    ],
)
def test_post_order_with_invalid_body_or_unknown_product_returns_422_and_stores_nothing(
    client, stack, payload
):
    request = body(**payload)
    if request["customerName"] is None:
        del request["customerName"]

    response = client.post("/api/orders", json=request)

    assert response.status_code == 422
    assert stack.orders.list_by_date("2026-06-10") == []


def test_post_order_when_stock_retries_exhausted_returns_409(client, stack):
    stack.products.before_replace = stack.products.bump_etag

    response = client.post("/api/orders", json=body())

    assert response.status_code == 409
    assert stack.orders.list_by_date("2026-06-10") == []
    assert stack.products.get("croissant").variants[0].stock == 5


def test_post_order_as_admin_returns_403_and_stores_nothing(client, stack):
    headers = stack.headers_for("admin@example.com", ADMIN_ROLE)

    response = client.post("/api/orders", json=body(), headers=headers)

    assert response.status_code == 403
    assert response.json() == {"detail": "Admins cannot place orders"}
    assert stack.orders.list_by_date("2026-06-10") == []
