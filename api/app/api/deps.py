from collections.abc import Callable
from datetime import UTC, datetime
from functools import cache
from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.adapters.local_auth import LocalAuthProvider
from app.adapters.memory.images import MemoryImageStore
from app.adapters.memory.orders import MemoryOrderRepository
from app.adapters.memory.products import MemoryProductRepository
from app.adapters.memory.users import MemoryUserRepository
from app.core.settings import LOCAL_ENVIRONMENT, LOCAL_IMAGES_CONTAINER_URL, get_settings
from app.domain.errors import INVALID_CREDENTIALS, AuthenticationError
from app.ports.auth import AuthProvider, Principal
from app.ports.images import ImageStore
from app.ports.repositories import OrderRepository, ProductRepository, UserRepository


def _has_cosmos() -> bool:
    settings = get_settings()
    if settings.cosmos_connection_string:
        return True
    if settings.environment != LOCAL_ENVIRONMENT:
        raise RuntimeError("PDC_COSMOS_CONNECTION_STRING is required outside the local environment")
    return False


@cache
def get_product_repository() -> ProductRepository:
    if _has_cosmos():
        # Imported lazily so the memory path never loads the Azure SDK.
        from app.adapters.cosmos.client import get_container
        from app.adapters.cosmos.products import CONTAINER_NAME, CosmosProductRepository

        return CosmosProductRepository(get_container(CONTAINER_NAME))
    return MemoryProductRepository()


@cache
def get_order_repository() -> OrderRepository:
    if _has_cosmos():
        from app.adapters.cosmos.client import get_container
        from app.adapters.cosmos.orders import CONTAINER_NAME, CosmosOrderRepository

        return CosmosOrderRepository(get_container(CONTAINER_NAME))
    return MemoryOrderRepository()


@cache
def get_user_repository() -> UserRepository:
    if _has_cosmos():
        from app.adapters.cosmos.client import get_container
        from app.adapters.cosmos.users import CONTAINER_NAME, CosmosUserRepository

        return CosmosUserRepository(get_container(CONTAINER_NAME))
    return MemoryUserRepository()


@cache
def get_image_store() -> ImageStore:
    settings = get_settings()
    if settings.storage_connection_string:
        if (
            settings.environment != LOCAL_ENVIRONMENT
            and settings.images_container_url == LOCAL_IMAGES_CONTAINER_URL
        ):
            raise RuntimeError("PDC_IMAGES_CONTAINER_URL is required outside the local environment")
        from app.adapters.blob.images import BlobImageStore

        return BlobImageStore(settings.storage_connection_string, settings.images_container_url)
    if settings.environment != LOCAL_ENVIRONMENT:
        raise RuntimeError(
            "PDC_STORAGE_CONNECTION_STRING is required outside the local environment"
        )
    return MemoryImageStore(settings.images_container_url)


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
