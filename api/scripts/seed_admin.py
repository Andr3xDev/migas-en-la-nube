import os
from collections.abc import Mapping

from app.api.deps import get_auth_provider, get_user_repository
from app.core.settings import get_settings
from app.domain.errors import ConflictError
from app.ports.auth import AuthProvider


def seed_admin(env: Mapping[str, str], auth: AuthProvider) -> None:
    values = {}
    for name in ("ADMIN_EMAIL", "ADMIN_INITIAL_PASSWORD"):
        values[name] = env.get(name)
        if not values[name]:
            raise SystemExit(f"{name} is required")
    try:
        auth.register(values["ADMIN_EMAIL"], values["ADMIN_INITIAL_PASSWORD"], role="admin")
    except ConflictError:
        pass  # Already seeded: keep the existing user and password.


if __name__ == "__main__":
    if not get_settings().cosmos_connection_string:
        raise SystemExit("PDC_COSMOS_CONNECTION_STRING is required")
    seed_admin(os.environ, get_auth_provider(get_user_repository()))
