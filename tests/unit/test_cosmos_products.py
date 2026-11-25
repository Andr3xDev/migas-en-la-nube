import pytest
from azure.cosmos.exceptions import CosmosAccessConditionFailedError, CosmosResourceExistsError

from app.adapters.cosmos.products import CosmosProductRepository, to_document
from app.domain.errors import ConcurrencyConflictError, ConflictError
from app.domain.models import Product


class FailingContainer:
    def query_items(self, *args, **kwargs):
        return iter([])

    def create_item(self, body):
        raise CosmosResourceExistsError(status_code=409, message="exists")

    def replace_item(self, *args, **kwargs):
        raise CosmosAccessConditionFailedError(status_code=412, message="stale")


class FakeContainer:
    """Documents keyed by (category, id), like a container partitioned by /category."""

    def __init__(self, fail_delete_of=None):
        self.documents: dict[tuple[str, str], dict] = {}
        self.fail_delete_of = fail_delete_of

    def seed(self, product: Product) -> None:
        self.documents[(product.category, product.id)] = {**to_document(product), "_etag": "e"}

    def query_items(self, query, parameters=None, enable_cross_partition_query=False):
        if parameters is None:
            return iter(self.documents.values())
        wanted = parameters[0]["value"]
        return iter(d for d in self.documents.values() if d["id"] == wanted)

    def create_item(self, body):
        self.documents[(body["category"], body["id"])] = {**body, "_etag": "new"}
        return self.documents[(body["category"], body["id"])]

    def delete_item(self, item, partition_key):
        if partition_key == self.fail_delete_of:
            raise RuntimeError("delete failed")
        del self.documents[(partition_key, item)]


PRODUCT = Product(
    id="p1", name="n", category="c", description="d", image_url=None, prep_minutes=1, etag="e"
)


def moved(product: Product, category: str, etag: str = "e") -> Product:
    return Product(**{**product.__dict__, "category": category, "etag": etag})


def test_create_maps_409_to_conflict():
    with pytest.raises(ConflictError):
        CosmosProductRepository(FailingContainer()).create(PRODUCT)


def test_replace_maps_412_to_concurrency_conflict():
    with pytest.raises(ConcurrencyConflictError):
        CosmosProductRepository(FailingContainer()).replace(PRODUCT)


def test_get_returns_none_for_unknown_id():
    assert CosmosProductRepository(FakeContainer()).get("missing") is None


def test_create_rejects_id_existing_in_another_category():
    container = FakeContainer()
    container.seed(PRODUCT)
    with pytest.raises(ConflictError):
        CosmosProductRepository(container).create(moved(PRODUCT, "other"))
    assert list(container.documents) == [("c", "p1")]


def test_move_across_categories_copies_then_deletes_old():
    container = FakeContainer()
    container.seed(PRODUCT)
    result = CosmosProductRepository(container).move(moved(PRODUCT, "other"))
    assert result.category == "other"
    assert list(container.documents) == [("other", "p1")]


def test_move_deletes_new_copy_when_old_delete_fails():
    container = FakeContainer(fail_delete_of="c")
    container.seed(PRODUCT)
    with pytest.raises(RuntimeError):
        CosmosProductRepository(container).move(moved(PRODUCT, "other"))
    assert list(container.documents) == [("c", "p1")]


def test_move_with_stale_etag_raises_concurrency_conflict():
    container = FakeContainer()
    container.seed(PRODUCT)
    with pytest.raises(ConcurrencyConflictError):
        CosmosProductRepository(container).move(moved(PRODUCT, "other", etag="stale"))
    assert list(container.documents) == [("c", "p1")]
