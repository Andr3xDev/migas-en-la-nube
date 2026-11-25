from datetime import UTC, datetime
from functools import cache

from app.adapters.memory.orders import MemoryOrderRepository
from app.adapters.memory.products import MemoryProductRepository
from app.core.settings import Settings
from app.ports.repositories import OrderRepository, ProductRepository


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


def get_now() -> datetime:
    return datetime.now(UTC)
