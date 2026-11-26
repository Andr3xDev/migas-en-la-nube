from dataclasses import replace

import pytest
from azure.core import MatchConditions
from azure.cosmos.exceptions import (
    CosmosAccessConditionFailedError,
    CosmosResourceExistsError,
    CosmosResourceNotFoundError,
)

from app.adapters.cosmos.products import CosmosProductRepository, to_document
from app.domain.errors import ConcurrencyConflictError, ConflictError, NotFoundError
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
        self.queries: list[tuple[str, bool]] = []
        self.replace_calls: list[dict] = []

    def replace_item(self, item, body, etag, match_condition):
        self.replace_calls.append({"etag": etag, "match_condition": match_condition})
        self.documents[(body["category"], body["id"])] = {**body, "_etag": "new"}
        return self.documents[(body["category"], body["id"])]

    def seed(self, product: Product) -> None:
        self.documents[(product.category, product.id)] = {**to_document(product), "_etag": "e"}

    def query_items(self, query, parameters=None, enable_cross_partition_query=False):
        self.queries.append((query, enable_cross_partition_query))
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


def test_move_keeps_original_error_when_compensating_delete_also_fails():
    class Container(FakeContainer):
        def delete_item(self, item, partition_key):
            raise RuntimeError("original" if partition_key == "c" else "compensation")

    container = Container()
    container.seed(PRODUCT)
    with pytest.raises(RuntimeError, match="original"):
        CosmosProductRepository(container).move(moved(PRODUCT, "other"))


@pytest.mark.parametrize(
    "operation",
    [
        lambda repository: repository.delete("p1"),
        lambda repository: repository.move(moved(PRODUCT, "other")),
    ],
    ids=["delete", "move"],
)
def test_delete_and_move_map_missing_document_to_not_found(operation):
    class VanishingContainer(FakeContainer):
        def delete_item(self, item, partition_key):
            raise CosmosResourceNotFoundError(status_code=404, message="gone")

    container = VanishingContainer()
    container.seed(PRODUCT)
    with pytest.raises(NotFoundError):
        operation(CosmosProductRepository(container))


def test_replace_maps_404_to_not_found():
    class MissingContainer(FailingContainer):
        def replace_item(self, *args, **kwargs):
            raise CosmosResourceNotFoundError(status_code=404, message="gone")

    with pytest.raises(NotFoundError):
        CosmosProductRepository(MissingContainer()).replace(PRODUCT)


def test_replace_sends_etag_with_if_not_modified_condition():
    container = FakeContainer()
    container.seed(PRODUCT)

    result = CosmosProductRepository(container).replace(PRODUCT)

    assert container.replace_calls == [
        {"etag": "e", "match_condition": MatchConditions.IfNotModified}
    ]
    assert result.etag == "new"


def test_list_all_queries_every_partition():
    container = FakeContainer()
    container.seed(PRODUCT)
    container.seed(moved(replace(PRODUCT, id="p2"), "other"))

    products = CosmosProductRepository(container).list_all()

    assert sorted(p.id for p in products) == ["p1", "p2"]
    assert container.queries == [("SELECT * FROM c", True)]


def test_move_within_same_category_replaces_in_place_without_delete():
    container = FakeContainer(fail_delete_of="c")
    container.seed(PRODUCT)

    result = CosmosProductRepository(container).move(replace(PRODUCT, name="renamed"))

    assert result.name == "renamed"
    assert container.replace_calls[0]["match_condition"] == MatchConditions.IfNotModified
    assert list(container.documents) == [("c", "p1")]


def test_move_with_stale_etag_raises_concurrency_conflict():
    container = FakeContainer()
    container.seed(PRODUCT)
    with pytest.raises(ConcurrencyConflictError):
        CosmosProductRepository(container).move(moved(PRODUCT, "other", etag="stale"))
    assert list(container.documents) == [("c", "p1")]
