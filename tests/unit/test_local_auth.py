from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.adapters.local_auth import LocalAuthProvider
from app.adapters.memory.users import MemoryUserRepository
from app.domain.errors import AuthenticationError, ConflictError

KEY = "unit-test-signing-key-32-bytes-min!"
DELAY = 0.25
PASSWORD = "correct horse"


@pytest.fixture
def sleeps() -> list[float]:
    return []


@pytest.fixture
def users() -> MemoryUserRepository:
    return MemoryUserRepository()


@pytest.fixture
def auth(users, sleeps) -> LocalAuthProvider:
    return LocalAuthProvider(
        users, KEY, login_failure_delay_seconds=DELAY, sleep=lambda seconds: sleeps.append(seconds)
    )


def test_register_same_password_twice_stores_distinct_scrypt_hashes(auth, users):
    auth.register("a@example.com", PASSWORD)
    auth.register("b@example.com", PASSWORD)

    first = users.get_by_email("a@example.com").password_hash
    second = users.get_by_email("b@example.com").password_hash
    assert first != second
    assert PASSWORD not in first
    assert first.startswith("scrypt$16384$8$1$")


def test_register_creates_customer_with_normalized_email(auth):
    user = auth.register("  Ana@Example.com ", PASSWORD)

    assert (user.email, user.role) == ("ana@example.com", "customer")


def test_register_duplicate_email_in_other_case_raises_conflict(auth):
    auth.register("ana@example.com", PASSWORD)

    with pytest.raises(ConflictError):
        auth.register("ANA@example.com", PASSWORD)


def test_login_is_case_insensitive_and_token_carries_claims_for_one_hour(auth):
    user = auth.register("ana@example.com", PASSWORD)

    token = auth.login("ANA@Example.com", PASSWORD)

    claims = jwt.decode(token, KEY, algorithms=["HS256"])
    assert (claims["sub"], claims["email"], claims["role"]) == (user.id, user.email, "customer")
    assert claims["exp"] - claims["iat"] == 3600


def test_login_failures_raise_identical_errors_and_sleep_once_each(auth, sleeps):
    auth.register("ana@example.com", PASSWORD)

    with pytest.raises(AuthenticationError) as unknown:
        auth.login("nobody@example.com", PASSWORD)
    with pytest.raises(AuthenticationError) as wrong:
        auth.login("ana@example.com", "wrong password")

    assert str(unknown.value) == str(wrong.value)
    assert sleeps == [DELAY, DELAY]


def test_login_success_does_not_sleep(auth, sleeps):
    auth.register("ana@example.com", PASSWORD)

    auth.login("ana@example.com", PASSWORD)

    assert sleeps == []


def test_verify_token_returns_principal_from_claims(auth):
    user = auth.register("ana@example.com", PASSWORD, role="admin")

    principal = auth.verify_token(auth.login("ana@example.com", PASSWORD))

    assert (principal.user_id, principal.email, principal.role) == (user.id, user.email, "admin")


def test_verify_token_signed_with_other_key_is_rejected(auth):
    forged = jwt.encode({"sub": "u1", "exp": datetime.now(UTC) + timedelta(hours=1)}, "x" * 40)

    with pytest.raises(AuthenticationError):
        auth.verify_token(forged)


def test_verify_token_expired_is_rejected(auth):
    expired = jwt.encode(
        {"sub": "u1", "email": "a@example.com", "role": "customer",
         "exp": datetime.now(UTC) - timedelta(seconds=5)},
        KEY,
    )  # fmt: skip

    with pytest.raises(AuthenticationError):
        auth.verify_token(expired)


def test_empty_jwt_key_allows_register_but_login_and_verify_raise_value_error(users):
    keyless = LocalAuthProvider(users, "", login_failure_delay_seconds=0, sleep=lambda _: None)

    keyless.register("ana@example.com", PASSWORD)

    with pytest.raises(ValueError):
        keyless.login("ana@example.com", PASSWORD)
    with pytest.raises(ValueError):
        keyless.verify_token("any.token.value")
