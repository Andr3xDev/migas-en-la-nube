import sys

import pytest

EMAIL = "Admin@Example.com"
PASSWORD = "initial-admin-pass"


@pytest.fixture
def seeding():
    # test_health purges app.*; a cached seed module would hold stale error classes.
    sys.modules.pop("scripts.seed_admin", None)
    from app.adapters.local_auth import LocalAuthProvider
    from app.adapters.memory.users import MemoryUserRepository
    from scripts.seed_admin import seed_admin

    users = MemoryUserRepository()
    auth = LocalAuthProvider(
        users,
        "seed-test-signing-key-32-bytes-min",
        login_failure_delay_seconds=0,
        sleep=lambda _: None,
    )
    return seed_admin, auth, users


def test_seed_admin_first_run_creates_admin_who_can_log_in(seeding):
    seed_admin, auth, users = seeding

    seed_admin({"ADMIN_EMAIL": EMAIL, "ADMIN_INITIAL_PASSWORD": PASSWORD}, auth)

    assert users.get_by_email("admin@example.com").role == "admin"
    assert auth.login(EMAIL, PASSWORD)


def test_seed_admin_rerun_is_idempotent(seeding):
    seed_admin, auth, users = seeding
    env = {"ADMIN_EMAIL": EMAIL, "ADMIN_INITIAL_PASSWORD": PASSWORD}
    seed_admin(env, auth)

    seed_admin(env, auth)

    assert users.get_by_email("admin@example.com").role == "admin"
    assert auth.login(EMAIL, PASSWORD)


def test_seed_admin_promotes_existing_customer_and_replaces_password(seeding):
    seed_admin, auth, users = seeding
    from app.domain.errors import AuthenticationError

    customer = auth.register(EMAIL, "old-customer-pass")
    customer_id = customer.id

    seed_admin({"ADMIN_EMAIL": EMAIL, "ADMIN_INITIAL_PASSWORD": PASSWORD}, auth)

    promoted = users.get_by_email("admin@example.com")
    assert promoted.id == customer_id
    assert promoted.role == "admin"
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
    seed_admin, auth, users = seeding

    with pytest.raises(SystemExit) as exit_info:
        seed_admin(env, auth)

    assert missing in str(exit_info.value.code)
    assert users.get_by_email("admin@example.com") is None
