from functools import cache

from azure.cosmos import CosmosClient
from azure.cosmos.container import ContainerProxy

from app.core.settings import get_settings

DATABASE_NAME = "migas"


@cache
def get_client() -> CosmosClient:
    return CosmosClient.from_connection_string(get_settings().cosmos_connection_string)


def get_container(name: str) -> ContainerProxy:
    return get_client().get_database_client(DATABASE_NAME).get_container_client(name)
