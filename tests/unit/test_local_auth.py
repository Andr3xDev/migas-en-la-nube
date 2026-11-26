from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.adapters.local_auth import LocalAuthProvider, verify_password
from app.adapters.memory.users import MemoryUserRepository
from app.domain.errors import AuthenticationError, ConflictError
from app.domain.models import ADMIN_ROLE, CUSTOMER_ROLE

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
    assert first.startswith("scrypt$")
    assert verify_password(PASSWORD, first)


def test_register_creates_customer_with_normalized_email(auth):
    user = auth.register("  Ana@Example.com ", PASSWORD)

    assert (user.email, user.role) == ("ana@example.com", CUSTOMER_ROLE)


def test_register_duplicate_email_in_other_case_raises_conflict(auth):
    auth.register("ana@example.com", PASSWORD)

    with pytest.raises(ConflictError):
        auth.register("ANA@example.com", PASSWORD)


def test_login_is_case_insensitive_and_token_carries_claims_for_one_hour(auth):
    user = auth.register("ana@example.com", PASSWORD)

    token = auth.login("ANA@Example.com", PASSWORD)

    claims = jwt.decode(token, KEY, algorithms=["HS256"])
    assert (claims["sub"], claims["email"], claims["role"]) == (user.id, user.email, CUSTOMER_ROLE)
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
    user = auth.register("ana@example.com", PASSWORD, role=ADMIN_ROLE)

    principal = auth.verify_token(auth.login("ana@example.com", PASSWORD))

    assert (principal.user_id, principal.email, principal.role) == (user.id, user.email, ADMIN_ROLE)


def valid_claims() -> dict:
    return {
        "sub": "u1",
        "email": "a@example.com",
        "role": CUSTOMER_ROLE,
        "exp": datetime.now(UTC) + timedelta(hours=1),
    }


def test_verify_token_signed_with_other_key_is_rejected(auth):
    forged = jwt.encode(valid_claims(), "x" * 40)

    with pytest.raises(AuthenticationError):
        auth.verify_token(forged)


def test_verify_token_expired_is_rejected(auth):
    expired = jwt.encode({**valid_claims(), "exp": datetime.now(UTC) - timedelta(seconds=5)}, KEY)

    with pytest.raises(AuthenticationError):
        auth.verify_token(expired)


@pytest.mark.parametrize("missing_claim", ["exp", "sub", "email", "role"])
def test_verify_token_without_required_claim_is_rejected(auth, missing_claim):
    claims = valid_claims()
    del claims[missing_claim]

    with pytest.raises(AuthenticationError):
        auth.verify_token(jwt.encode(claims, KEY))


@pytest.mark.filterwarnings("ignore:The HMAC key is:UserWarning")
@pytest.mark.parametrize(
    "algorithm, key", [("none", None), ("HS512", KEY)], ids=["unsigned", "other-hmac"]
)
def test_verify_token_with_unpinned_algorithm_is_rejected(auth, algorithm, key):
    token = jwt.encode(valid_claims(), key, algorithm=algorithm)

    with pytest.raises(AuthenticationError):
        auth.verify_token(token)


def test_verify_password_with_malformed_stored_hash_returns_false():
    assert verify_password("x", "garbage") is False


def test_empty_jwt_key_allows_register_but_login_and_verify_raise_value_error(users):
    keyless = LocalAuthProvider(users, "", login_failure_delay_seconds=0, sleep=lambda _: None)

    keyless.register("ana@example.com", PASSWORD)

    with pytest.raises(ValueError):
        keyless.login("ana@example.com", PASSWORD)
    with pytest.raises(ValueError):
        keyless.verify_token("any.token.value")
