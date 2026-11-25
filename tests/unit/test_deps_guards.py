import pytest

from app.api import deps
from app.core.settings import Settings

REPOSITORY_FACTORIES = [
    deps.get_product_repository,
    deps.get_order_repository,
    deps.get_user_repository,
]


@pytest.mark.parametrize("factory", REPOSITORY_FACTORIES)
def test_repository_requires_cosmos_connection_string_outside_local(factory, monkeypatch):
    monkeypatch.setattr(deps, "get_settings", lambda: Settings(environment="prod"))
    factory.cache_clear()

    with pytest.raises(RuntimeError, match="PDC_COSMOS_CONNECTION_STRING"):
        factory()


def test_image_store_requires_container_url_outside_local(monkeypatch):
    settings = Settings(environment="prod", storage_connection_string="UseDevelopmentStorage=true")
    monkeypatch.setattr(deps, "get_settings", lambda: settings)
    deps.get_image_store.cache_clear()

    with pytest.raises(RuntimeError, match="PDC_IMAGES_CONTAINER_URL"):
        deps.get_image_store()
