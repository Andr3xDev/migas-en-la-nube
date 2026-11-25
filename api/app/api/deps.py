from collections.abc import Callable
from datetime import UTC, datetime
from functools import cache
from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.adapters.local_auth import LocalAuthProvider
from app.adapters.memory.orders import MemoryOrderRepository
from app.adapters.memory.products import MemoryProductRepository
from app.adapters.memory.users import MemoryUserRepository
from app.core.settings import Settings
from app.domain.errors import INVALID_CREDENTIALS, AuthenticationError
from app.ports.auth import AuthProvider, Principal
from app.ports.repositories import OrderRepository, ProductRepository, UserRepository


@cache
def get_settings() -> Settings:
    return Settings()


@cache
def get_product_repository() -> ProductRepository:
    if get_settings().cosmos_connection_string:
        # Imported lazily so the memory path never loads the Azure SDK.
        from app.adapters.cosmos.client import get_container
        from app.adapters.cosmos.products import CONTAINER_NAME, CosmosProductRepository

        return CosmosProductRepository(get_container(CONTAINER_NAME))
    return MemoryProductRepository()


@cache
def get_order_repository() -> OrderRepository:
    if get_settings().cosmos_connection_string:
        from app.adapters.cosmos.client import get_container
        from app.adapters.cosmos.orders import CONTAINER_NAME, CosmosOrderRepository

        return CosmosOrderRepository(get_container(CONTAINER_NAME))
    return MemoryOrderRepository()


@cache
def get_user_repository() -> UserRepository:
    if get_settings().cosmos_connection_string:
        from app.adapters.cosmos.client import get_container
        from app.adapters.cosmos.users import CONTAINER_NAME, CosmosUserRepository

        return CosmosUserRepository(get_container(CONTAINER_NAME))
    return MemoryUserRepository()


@cache
def get_auth_provider(
    users: Annotated[UserRepository, Depends(get_user_repository)],
) -> AuthProvider:
    settings = get_settings()
    return LocalAuthProvider(
        users,
        settings.jwt_key,
        login_failure_delay_seconds=settings.login_failure_delay_seconds,
    )


bearer_scheme = HTTPBearer(auto_error=False)


def get_optional_principal(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    auth: Annotated[AuthProvider, Depends(get_auth_provider)],
) -> Principal | None:
    return auth.verify_token(credentials.credentials) if credentials else None


def current_user(
    principal: Annotated[Principal | None, Depends(get_optional_principal)],
) -> Principal:
    if principal is None:
        raise AuthenticationError(INVALID_CREDENTIALS)
    return principal


def require_role(role: str) -> Callable[..., Principal]:
    def check(principal: Annotated[Principal, Depends(current_user)]) -> Principal:
        if principal.role != role:
            raise HTTPException(status_code=403, detail="Forbidden")
        return principal

    return check


def get_now() -> datetime:
    return datetime.now(UTC)
