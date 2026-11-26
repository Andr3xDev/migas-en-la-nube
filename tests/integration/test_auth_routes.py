from datetime import UTC, datetime, timedelta, timezone

import jwt
import pytest

from app.api.deps import get_now
from app.domain.models import ADMIN_ROLE, CUSTOMER_ROLE

SHOP_TZ = timezone(timedelta(hours=-5))
NOW = datetime(2026, 6, 10, 12, 0, tzinfo=SHOP_TZ)
ORDER_BODY = {
    "customerName": "Ana",
    "phone": "3001234567",
    "pickupTime": "2026-06-10T13:00:00-05:00",
    "items": [{"productId": "croissant", "variantName": "Single", "quantity": 1}],
}


@pytest.fixture
def stack(stack, client):
    client.app.dependency_overrides[get_now] = lambda: NOW
    return stack


def expired_token(key: str) -> str:
    claims = {"sub": "u1", "email": "a@example.com", "role": CUSTOMER_ROLE}
    return jwt.encode({**claims, "exp": datetime.now(UTC) - timedelta(minutes=1)}, key)


def forged_token(key: str) -> str:
    claims = {"sub": "u1", "email": "a@example.com", "role": ADMIN_ROLE}
    return jwt.encode({**claims, "exp": datetime.now(UTC) + timedelta(hours=1)}, f"not-{key}")


def test_register_returns_201_with_lowercase_email_and_no_secrets(client, stack):
    response = client.post(
        "/api/auth/register", json={"email": "Ana@Example.com", "password": stack.password}
    )

    assert response.status_code == 201
    data = response.json()
    assert set(data) == {"id", "email", "role"}
    assert (data["email"], data["role"]) == ("ana@example.com", "customer")


def test_register_with_role_in_body_still_creates_customer(client, stack):
    response = client.post(
        "/api/auth/register",
        json={"email": "ana@example.com", "password": stack.password, "role": "admin"},
    )

    assert response.json()["role"] == "customer"


@pytest.mark.parametrize(
    "payload",
    [
        {"email": "not-an-email", "password": "correct horse"},
        {"email": "ana@example.com", "password": "1234567"},
        {"email": "ana@example.com", "password": "x" * 1025},
    ],
)
def test_register_with_invalid_input_returns_422_and_creates_no_user(client, stack, payload):
    response = client.post("/api/auth/register", json=payload)

    assert response.status_code == 422
    assert stack.users.get_by_email("ana@example.com") is None


@pytest.mark.parametrize("length", [8, 1024])
def test_register_accepts_password_length_boundaries(client, stack, length):
    response = client.post(
        "/api/auth/register", json={"email": "ana@example.com", "password": "x" * length}
    )

    assert response.status_code == 201


def test_register_duplicate_email_in_other_case_returns_409(client, stack):
    client.post("/api/auth/register", json={"email": "ana@example.com", "password": stack.password})

    response = client.post(
        "/api/auth/register", json={"email": "ANA@example.com", "password": stack.password}
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "Email already registered"}
    assert "ana@example.com" not in response.text.lower()


def test_login_returns_200_with_access_token(client, stack):
    client.post("/api/auth/register", json={"email": "ana@example.com", "password": stack.password})

    response = client.post(
        "/api/auth/login", json={"email": "ANA@example.com", "password": stack.password}
    )

    assert response.status_code == 200
    me = client.get(
        "/api/me/orders", headers={"X-Pdc-Token": f"Bearer {response.json()['accessToken']}"}
    )
    assert me.status_code == 200


def test_login_unknown_email_and_wrong_password_return_identical_401(client, stack):
    client.post("/api/auth/register", json={"email": "ana@example.com", "password": stack.password})

    unknown = client.post(
        "/api/auth/login", json={"email": "no@example.com", "password": stack.password}
    )
    wrong = client.post(
        "/api/auth/login", json={"email": "ana@example.com", "password": "wrong-one"}
    )

    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json() == wrong.json()


def test_post_order_with_session_links_order_to_user(client, stack):
    response = client.post(
        "/api/orders", json=ORDER_BODY, headers=stack.headers_for("ana@example.com")
    )

    assert response.status_code == 201
    [order] = stack.orders.list_by_user(stack.users.get_by_email("ana@example.com").id)
    assert order.id == response.json()["code"]


def test_post_order_as_guest_stores_no_owner(client, stack):
    client.post("/api/orders", json=ORDER_BODY)

    assert [o.user_id for o in stack.orders.list_by_date("2026-06-10")] == [None]


def test_authorization_header_is_ignored_for_guest_order(client, stack):
    garbage = {"Authorization": "Bearer garbage"}

    response = client.post("/api/orders", json=ORDER_BODY, headers=garbage)

    assert response.status_code == 201
    assert [o.user_id for o in stack.orders.list_by_date("2026-06-10")] == [None]


def test_authorization_header_alone_does_not_authenticate_me_route(client, stack):
    token = stack.headers_for("ana@example.com")["X-Pdc-Token"].removeprefix("Bearer ")
    valid_in_wrong_header = {"Authorization": f"Bearer {token}"}

    assert client.get("/api/me/orders", headers=valid_in_wrong_header).status_code == 401


def test_token_scheme_is_case_insensitive(client, stack):
    token = stack.headers_for("ana@example.com")["X-Pdc-Token"].removeprefix("Bearer ")

    response = client.get("/api/me/orders", headers={"X-Pdc-Token": f"bearer {token}"})

    assert response.status_code == 200


def test_invalid_bearer_token_on_me_route_returns_401(client, stack):
    response = client.get("/api/me/orders", headers={"X-Pdc-Token": "Bearer garbage"})

    assert response.status_code == 401


@pytest.mark.parametrize("value", ["Basic abc", "garbage", "Bearer ", "Bearer"])
def test_malformed_token_header_on_order_returns_401_not_guest_fallback(client, stack, value):
    response = client.post("/api/orders", json=ORDER_BODY, headers={"X-Pdc-Token": value})

    assert response.status_code == 401
    assert stack.orders.list_by_date("2026-06-10") == []


@pytest.mark.parametrize("token", [expired_token, forged_token])
def test_post_order_with_invalid_token_returns_401_and_stores_nothing(client, stack, token):
    headers = {"X-Pdc-Token": f"Bearer {token(stack.key)}"}

    response = client.post("/api/orders", json=ORDER_BODY, headers=headers)

    assert response.status_code == 401
    assert stack.orders.list_by_date("2026-06-10") == []
