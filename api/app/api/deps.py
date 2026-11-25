from functools import cache

from app.adapters.memory.products import MemoryProductRepository
from app.core.settings import Settings
from app.ports.repositories import ProductRepository


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
