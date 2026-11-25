from datetime import datetime, timedelta, timezone

import pytest

SHOP_TZ = timezone(timedelta(hours=-5))
NOW = datetime(2026, 6, 10, 12, 0, tzinfo=SHOP_TZ)
PICKUP = "2026-06-10T13:00:00-05:00"


@pytest.fixture
def stores(client):
    # Imported after `client` so both come from the same app.* module instances.
    from app.adapters.memory.orders import MemoryOrderRepository
    from app.adapters.memory.products import MemoryProductRepository
    from app.api.deps import get_now, get_order_repository, get_product_repository
    from app.domain.models import Product, Variant

    products = MemoryProductRepository()
    orders = MemoryOrderRepository()
    products.create(
        Product(
            "croissant", "Croissant", "bakery", "Buttery", None, 90, [Variant("Single", 6000, 5)]
        )
    )
    overrides = client.app.dependency_overrides
    overrides[get_product_repository] = lambda: products
    overrides[get_order_repository] = lambda: orders
    overrides[get_now] = lambda: NOW
    return products, orders


def body(**changes):
    payload = {
        "customerName": "Ana",
        "phone": "3001234567",
        "pickupTime": PICKUP,
        "items": [{"productId": "croissant", "variantName": "Single", "quantity": 2}],
    }
    return {**payload, **changes}


def test_post_order_as_guest_returns_201_with_code_and_total(client, stores):
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
    ],
)
def test_post_order_with_invalid_body_or_unknown_product_returns_422_and_stores_nothing(
    client, stores, payload
):
    _, orders = stores
    request = body(**payload)
    if request["customerName"] is None:
        del request["customerName"]

    response = client.post("/api/orders", json=request)

    assert response.status_code == 422
    assert orders.list_by_date("2026-06-10") == []


def test_post_order_when_stock_retries_exhausted_returns_409(client, stores):
    products, orders = stores
    products.before_replace = products.bump_etag

    response = client.post("/api/orders", json=body())

    assert response.status_code == 409
    assert orders.list_by_date("2026-06-10") == []
    assert products.get("croissant").variants[0].stock == 5
