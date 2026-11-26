import pytest

from app.adapters.local_auth import LocalAuthProvider
from app.adapters.memory.users import MemoryUserRepository
from app.domain.errors import AuthenticationError, ConflictError
from app.domain.models import ADMIN_ROLE, User
from scripts.seed_admin import seed_admin

EMAIL = "Admin@Example.com"
PASSWORD = "initial-admin-pass"


@pytest.fixture
def seeding():
    users = MemoryUserRepository()
    auth = LocalAuthProvider(
        users,
        "seed-test-signing-key-32-bytes-min",
        login_failure_delay_seconds=0,
        sleep=lambda _: None,
    )
    return auth, users


def test_seed_admin_first_run_creates_admin_who_can_log_in(seeding):
    auth, users = seeding

    seed_admin({"ADMIN_EMAIL": EMAIL, "ADMIN_INITIAL_PASSWORD": PASSWORD}, auth)

    assert users.get_by_email("admin@example.com").role == ADMIN_ROLE
    assert auth.login(EMAIL, PASSWORD)


def test_seed_admin_rerun_is_idempotent(seeding):
    auth, users = seeding
    env = {"ADMIN_EMAIL": EMAIL, "ADMIN_INITIAL_PASSWORD": PASSWORD}
    seed_admin(env, auth)

    etag_after_first_run = users.get_by_email("admin@example.com").etag

    seed_admin(env, auth)

    admin = users.get_by_email("admin@example.com")
    assert admin.role == ADMIN_ROLE
    assert admin.etag == etag_after_first_run
    assert auth.login(EMAIL, PASSWORD)


def test_seed_admin_rerun_with_new_password_replaces_it_and_keeps_admin_role(seeding):
    auth, users = seeding
    seed_admin({"ADMIN_EMAIL": EMAIL, "ADMIN_INITIAL_PASSWORD": PASSWORD}, auth)

    seed_admin({"ADMIN_EMAIL": EMAIL, "ADMIN_INITIAL_PASSWORD": "rotated-admin-pass"}, auth)

    assert users.get_by_email("admin@example.com").role == ADMIN_ROLE
    assert auth.login(EMAIL, "rotated-admin-pass")
    with pytest.raises(AuthenticationError):
        auth.login(EMAIL, PASSWORD)


def test_seed_admin_retries_when_user_appears_between_read_and_create(seeding):
    auth, users = seeding

    real_create = users.create
    calls = []

    def racing_create(user):
        calls.append(user)
        if len(calls) == 1:
            # Another process wins the race: the customer exists before our create lands.
            real_create(User(id="other", email=user.email, password_hash="x"))
            raise ConflictError("exists")
        return real_create(user)

    users.create = racing_create

    seed_admin({"ADMIN_EMAIL": EMAIL, "ADMIN_INITIAL_PASSWORD": PASSWORD}, auth)

    promoted = users.get_by_email("admin@example.com")
    assert promoted.id == "other"
    assert promoted.role == ADMIN_ROLE
    assert auth.login(EMAIL, PASSWORD)


def test_seed_admin_promotes_existing_customer_and_replaces_password(seeding):
    auth, users = seeding

    customer = auth.register(EMAIL, "old-customer-pass")
    customer_id = customer.id
    customer.favorites = ["product-1"]
    users.replace(customer)

    seed_admin({"ADMIN_EMAIL": EMAIL, "ADMIN_INITIAL_PASSWORD": PASSWORD}, auth)

    promoted = users.get_by_email("admin@example.com")
    assert promoted.id == customer_id
    assert promoted.role == ADMIN_ROLE
    assert promoted.favorites == ["product-1"]
    assert auth.login(EMAIL, PASSWORD)
    with pytest.raises(AuthenticationError):
        auth.login(EMAIL, "old-customer-pass")


@pytest.mark.parametrize(
    ("env", "missing"),
    [
        ({"ADMIN_EMAIL": EMAIL}, "ADMIN_INITIAL_PASSWORD"),
        ({"ADMIN_EMAIL": EMAIL, "ADMIN_INITIAL_PASSWORD": ""}, "ADMIN_INITIAL_PASSWORD"),
        ({"ADMIN_INITIAL_PASSWORD": PASSWORD}, "ADMIN_EMAIL"),
    ],
)
def test_seed_admin_missing_variable_exits_naming_it_and_creates_no_user(seeding, env, missing):
    auth, users = seeding

    with pytest.raises(SystemExit) as exit_info:
        seed_admin(env, auth)

    assert missing in str(exit_info.value.code)
    assert users.get_by_email("admin@example.com") is None
