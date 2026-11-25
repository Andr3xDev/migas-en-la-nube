from datetime import datetime, timedelta, timezone

import pytest

KEY = "route-test-signing-key-32-bytes-min"
PASSWORD = "correct horse"
SHOP_TZ = timezone(timedelta(hours=-5))
CONTAINER_URL = "https://migasdev.blob.core.windows.net/images"
IMAGE_URL = f"{CONTAINER_URL}/products/croissant/a.png"
DAY = "2026-11-27"
PRODUCT_BODY = {
    "name": "Pan de bono",
    "category": "bakery",
    "description": "Cheesy",
    "imageUrl": IMAGE_URL,
    "prepMinutes": 30,
    "variants": [{"name": "Single", "price": 3000, "stock": 4}],
}
ADMIN_ROUTES = [
    ("POST", "/api/admin/products", {"json": PRODUCT_BODY}),
    ("PUT", "/api/admin/products/croissant", {"json": PRODUCT_BODY}),
    ("DELETE", "/api/admin/products/croissant", {}),
    (
        "POST",
        "/api/admin/products/croissant/image-upload-url",
        {"json": {"contentType": "image/png"}},
    ),
    ("GET", f"/api/admin/orders?date={DAY}", {}),
    ("PATCH", f"/api/admin/orders/ORDER001/status?date={DAY}", {"json": {"status": "preparing"}}),
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
        get_image_store,
        get_order_repository,
        get_product_repository,
        get_settings,
        get_user_repository,
    )
    from app.core.settings import Settings
    from app.domain.models import Order, OrderItem, Product, Variant
    from app.ports.images import ImageUpload

    class FakeImageStore:
        def create_upload(self, product_id, content_type):
            return ImageUpload(
                "https://upload?sig=x", IMAGE_URL, datetime(2026, 11, 25, 12, 5, tzinfo=SHOP_TZ)
            )

        def delete_product_images(self, product_id):
            pass

    users = MemoryUserRepository()
    products = MemoryProductRepository()
    products.create(
        Product("croissant", "Croissant", "bakery", "d", None, 90, [Variant("Single", 6000, 5)])
    )
    orders = MemoryOrderRepository()
    for code, day, hour in [
        ("LATE0000", DAY, 15),
        ("EARLY000", DAY, 9),
        ("NEXTDAY0", "2026-11-28", 8),
    ]:
        orders.create(
            Order(
                id=code,
                customer_name="Ana",
                phone="300",
                pickup_time=datetime.fromisoformat(f"{day}T{hour:02d}:00:00-05:00"),
                pickup_date=day,
                items=[OrderItem("croissant", "Croissant", "Single", 6000, 1)],
                total=6000,
            )
        )
    orders.create(
        Order(
            id="ORDER001",
            customer_name="Beto",
            phone="301",
            pickup_time=datetime.fromisoformat(f"{DAY}T18:00:00-05:00"),
            pickup_date=DAY,
            items=[OrderItem("croissant", "Croissant", "Single", 6000, 1)],
            total=6000,
        )
    )
    auth = LocalAuthProvider(users, KEY, login_failure_delay_seconds=0, sleep=lambda _: None)
    overrides = client.app.dependency_overrides
    overrides[get_user_repository] = lambda: users
    overrides[get_auth_provider] = lambda: auth
    overrides[get_product_repository] = lambda: products
    overrides[get_order_repository] = lambda: orders
    overrides[get_image_store] = FakeImageStore
    overrides[get_settings] = lambda: Settings(images_container_url=CONTAINER_URL)
    return auth


def headers_for(auth, role: str) -> dict[str, str]:
    auth.register(f"{role}@example.com", PASSWORD, role=role)
    return {"Authorization": f"Bearer {auth.login(f'{role}@example.com', PASSWORD)}"}


@pytest.fixture
def admin(stack):
    return headers_for(stack, "admin")


@pytest.mark.parametrize(("method", "url", "kwargs"), ADMIN_ROUTES)
def test_admin_route_without_token_returns_401(client, stack, method, url, kwargs):
    assert client.request(method, url, **kwargs).status_code == 401


@pytest.mark.parametrize(("method", "url", "kwargs"), ADMIN_ROUTES)
def test_admin_route_with_customer_token_returns_403(client, stack, method, url, kwargs):
    response = client.request(method, url, headers=headers_for(stack, "customer"), **kwargs)

    assert response.status_code == 403


def test_create_product_returns_201_and_public_detail_shows_it(client, admin):
    response = client.post("/api/admin/products", json=PRODUCT_BODY, headers=admin)

    assert response.status_code == 201
    created = response.json()
    assert client.get(f"/api/products/{created['id']}").json() == created


@pytest.mark.parametrize(
    "changes",
    [
        {"variants": []},
        {"variants": [{"name": "A", "price": -1, "stock": 1}]},
        {"imageUrl": "https://evil.example.com/images/a.png"},
    ],
    ids=["no variants", "negative price", "foreign image host"],
)
def test_create_invalid_product_returns_422_and_stores_nothing(client, admin, changes):
    response = client.post("/api/admin/products", json={**PRODUCT_BODY, **changes}, headers=admin)

    assert response.status_code == 422
    assert [p["id"] for p in client.get("/api/products").json()] == ["croissant"]


def test_update_product_returns_200_and_public_detail_shows_new_values(client, admin):
    response = client.put("/api/admin/products/croissant", json=PRODUCT_BODY, headers=admin)

    assert response.status_code == 200
    detail = client.get("/api/products/croissant").json()
    assert (detail["name"], detail["variants"][0]["stock"]) == ("Pan de bono", 4)


def test_update_unknown_product_returns_404(client, admin):
    response = client.put("/api/admin/products/nope", json=PRODUCT_BODY, headers=admin)

    assert response.status_code == 404


def test_delete_product_returns_204_then_public_detail_is_404(client, admin):
    response = client.delete("/api/admin/products/croissant", headers=admin)

    assert response.status_code == 204
    assert client.get("/api/products/croissant").status_code == 404


def test_delete_unknown_product_returns_404(client, admin):
    assert client.delete("/api/admin/products/nope", headers=admin).status_code == 404


def test_image_upload_url_returns_upload_and_public_urls(client, admin):
    response = client.post(
        "/api/admin/products/croissant/image-upload-url",
        json={"contentType": "image/png"},
        headers=admin,
    )

    assert response.status_code == 200
    assert response.json() == {
        "uploadUrl": "https://upload?sig=x",
        "imageUrl": IMAGE_URL,
        "expiresAt": "2026-11-25T12:05:00-05:00",
    }


def test_image_upload_url_for_unknown_product_returns_404(client, admin):
    response = client.post(
        "/api/admin/products/nope/image-upload-url",
        json={"contentType": "image/png"},
        headers=admin,
    )

    assert response.status_code == 404


def test_list_orders_returns_only_requested_day_earliest_first_with_contact(client, admin):
    response = client.get(f"/api/admin/orders?date={DAY}", headers=admin)

    assert response.status_code == 200
    body = response.json()
    assert [o["code"] for o in body] == ["EARLY000", "LATE0000", "ORDER001"]
    assert (body[0]["customerName"], body[0]["phone"]) == ("Ana", "300")


@pytest.mark.parametrize("query", ["", "?date=2026-13-40"], ids=["missing", "invalid"])
def test_list_orders_with_missing_or_invalid_date_returns_422(client, admin, query):
    assert client.get(f"/api/admin/orders{query}", headers=admin).status_code == 422


def test_change_status_returns_200_with_new_status(client, admin):
    response = client.patch(
        f"/api/admin/orders/ORDER001/status?date={DAY}", json={"status": "preparing"}, headers=admin
    )

    assert response.status_code == 200
    assert response.json()["status"] == "preparing"


def test_change_status_with_wrong_date_returns_404(client, admin):
    response = client.patch(
        "/api/admin/orders/ORDER001/status?date=2026-11-28",
        json={"status": "preparing"},
        headers=admin,
    )

    assert response.status_code == 404


@pytest.mark.parametrize(
    ("status", "expected"), [("ready", 409), ("teleported", 422)], ids=["skipped", "unknown"]
)
def test_change_status_with_invalid_status_returns_error(client, admin, status, expected):
    response = client.patch(
        f"/api/admin/orders/ORDER001/status?date={DAY}", json={"status": status}, headers=admin
    )

    assert response.status_code == expected


def test_change_status_with_missing_date_returns_422(client, admin):
    response = client.patch(
        "/api/admin/orders/ORDER001/status", json={"status": "preparing"}, headers=admin
    )

    assert response.status_code == 422
