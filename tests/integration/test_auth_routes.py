from datetime import UTC, datetime, timedelta, timezone

import jwt
import pytest

KEY = "route-test-signing-key-32-bytes-min"
PASSWORD = "correct horse"
SHOP_TZ = timezone(timedelta(hours=-5))
NOW = datetime(2026, 6, 10, 12, 0, tzinfo=SHOP_TZ)
ORDER_BODY = {
    "customerName": "Ana",
    "phone": "3001234567",
    "pickupTime": "2026-06-10T13:00:00-05:00",
    "items": [{"productId": "croissant", "variantName": "Single", "quantity": 1}],
}


@pytest.fixture
def stack(client):
    # Imported after `client` so both come from the same app.* module instances.
    from app.adapters.local_auth import LocalAuthProvider
    from app.adapters.memory.orders import MemoryOrderRepository
    from app.adapters.memory.products import MemoryProductRepository
    from app.adapters.memory.users import MemoryUserRepository
    from app.api.deps import (
        get_auth_provider,
        get_now,
        get_order_repository,
        get_product_repository,
        get_user_repository,
    )
    from app.domain.models import Product, Variant

    users = MemoryUserRepository()
    orders = MemoryOrderRepository()
    products = MemoryProductRepository()
    products.create(
        Product(
            "croissant", "Croissant", "bakery", "Buttery", None, 90, [Variant("Single", 6000, 5)]
        )
    )
    auth = LocalAuthProvider(users, KEY, login_failure_delay_seconds=0, sleep=lambda _: None)
    overrides = client.app.dependency_overrides
    overrides[get_user_repository] = lambda: users
    overrides[get_auth_provider] = lambda: auth
    overrides[get_order_repository] = lambda: orders
    overrides[get_product_repository] = lambda: products
    overrides[get_now] = lambda: NOW
    return auth, users, orders


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def token_for(auth, email: str, role: str = "customer") -> str:
    auth.register(email, PASSWORD, role=role)
    return auth.login(email, PASSWORD)


def expired_token() -> str:
    claims = {"sub": "u1", "email": "a@example.com", "role": "customer"}
    return jwt.encode({**claims, "exp": datetime.now(UTC) - timedelta(minutes=1)}, KEY)


def forged_token() -> str:
    claims = {"sub": "u1", "email": "a@example.com", "role": "admin"}
    return jwt.encode({**claims, "exp": datetime.now(UTC) + timedelta(hours=1)}, "x" * 40)


@pytest.fixture
def admin_probe(client):
    from fastapi import Depends

    from app.api.deps import require_role

    client.app.add_api_route(
        "/api/admin/probe", lambda: {"ok": True}, dependencies=[Depends(require_role("admin"))]
    )


def test_register_returns_201_with_lowercase_email_and_no_secrets(client, stack):
    response = client.post(
        "/api/auth/register", json={"email": "Ana@Example.com", "password": PASSWORD}
    )

    assert response.status_code == 201
    data = response.json()
    assert set(data) == {"id", "email", "role"}
    assert (data["email"], data["role"]) == ("ana@example.com", "customer")


def test_register_with_role_in_body_still_creates_customer(client, stack):
    response = client.post(
        "/api/auth/register",
        json={"email": "ana@example.com", "password": PASSWORD, "role": "admin"},
    )

    assert response.json()["role"] == "customer"


@pytest.mark.parametrize(
    "payload",
    [
        {"email": "not-an-email", "password": PASSWORD},
        {"email": "ana@example.com", "password": "1234567"},
        {"email": "ana@example.com", "password": "x" * 1025},
    ],
)
def test_register_with_invalid_input_returns_422_and_creates_no_user(client, stack, payload):
    _, users, _ = stack

    response = client.post("/api/auth/register", json=payload)

    assert response.status_code == 422
    assert users.get_by_email("ana@example.com") is None


def test_register_duplicate_email_in_other_case_returns_409(client, stack):
    client.post("/api/auth/register", json={"email": "ana@example.com", "password": PASSWORD})

    response = client.post(
        "/api/auth/register", json={"email": "ANA@example.com", "password": PASSWORD}
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "Email already registered"}
    assert "ana@example.com" not in response.text.lower()


def test_default_auth_provider_without_jwt_key_can_register(client):
    from app.api.deps import get_auth_provider, get_user_repository
    from app.core.settings import get_settings

    get_settings.cache_clear()
    get_user_repository.cache_clear()
    get_auth_provider.cache_clear()
    try:
        provider = get_auth_provider(get_user_repository())

        assert provider.register("Admin@Example.com", PASSWORD, role="admin").role == "admin"
    finally:
        get_auth_provider.cache_clear()
        get_user_repository.cache_clear()
        get_settings.cache_clear()


def test_login_returns_200_with_access_token(client, stack):
    client.post("/api/auth/register", json={"email": "ana@example.com", "password": PASSWORD})

    response = client.post(
        "/api/auth/login", json={"email": "ANA@example.com", "password": PASSWORD}
    )

    assert response.status_code == 200
    assert (
        jwt.decode(response.json()["accessToken"], KEY, algorithms=["HS256"])["role"] == "customer"
    )


def test_login_unknown_email_and_wrong_password_return_identical_401(client, stack):
    client.post("/api/auth/register", json={"email": "ana@example.com", "password": PASSWORD})

    unknown = client.post("/api/auth/login", json={"email": "no@example.com", "password": PASSWORD})
    wrong = client.post(
        "/api/auth/login", json={"email": "ana@example.com", "password": "wrong-one"}
    )

    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json() == wrong.json()


def test_admin_route_without_token_returns_401(client, stack, admin_probe):
    assert client.get("/api/admin/probe").status_code == 401


@pytest.mark.parametrize("token", [expired_token, forged_token])
def test_admin_route_with_expired_or_tampered_token_returns_401(client, stack, admin_probe, token):
    assert client.get("/api/admin/probe", headers=bearer(token())).status_code == 401


def test_admin_route_with_customer_token_returns_403(client, stack, admin_probe):
    auth, _, _ = stack

    response = client.get("/api/admin/probe", headers=bearer(token_for(auth, "c@example.com")))

    assert response.status_code == 403


def test_admin_route_with_admin_token_is_processed(client, stack, admin_probe):
    auth, _, _ = stack

    response = client.get(
        "/api/admin/probe", headers=bearer(token_for(auth, "a@example.com", role="admin"))
    )

    assert response.status_code == 200


def test_post_order_with_session_links_order_to_user(client, stack):
    auth, users, orders = stack

    response = client.post(
        "/api/orders", json=ORDER_BODY, headers=bearer(token_for(auth, "ana@example.com"))
    )

    assert response.status_code == 201
    [order] = orders.list_by_user(users.get_by_email("ana@example.com").id)
    assert order.id == response.json()["code"]


def test_post_order_as_guest_stores_no_owner(client, stack):
    _, _, orders = stack

    client.post("/api/orders", json=ORDER_BODY)

    assert [o.user_id for o in orders.list_by_date("2026-06-10")] == [None]


@pytest.mark.parametrize("token", [expired_token, forged_token])
def test_post_order_with_invalid_token_returns_401_and_stores_nothing(client, stack, token):
    _, _, orders = stack

    response = client.post("/api/orders", json=ORDER_BODY, headers=bearer(token()))

    assert response.status_code == 401
    assert orders.list_by_date("2026-06-10") == []
