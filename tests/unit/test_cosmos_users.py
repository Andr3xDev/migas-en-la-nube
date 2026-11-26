import pytest
from azure.cosmos.exceptions import CosmosAccessConditionFailedError, CosmosResourceExistsError

from app.adapters.cosmos.users import CosmosUserRepository, to_document
from app.domain.errors import ConcurrencyConflictError, ConflictError
from app.domain.models import ADMIN_ROLE, User

USER = User(id="u1", email="ana@example.com", password_hash="hash", role=ADMIN_ROLE, etag="e1")


class FakeContainer:
    def __init__(self, documents=(), exists=False, stale=False):
        self.documents = list(documents)
        self.exists = exists
        self.stale = stale
        self.partition_key = None

    def query_items(self, query, parameters, partition_key):
        self.partition_key = partition_key
        return iter(self.documents)

    def create_item(self, body):
        if self.exists:
            raise CosmosResourceExistsError(status_code=409, message="exists")
        return {**body, "_etag": "e1", "_rid": "r", "_ts": 1}

    def replace_item(self, item, body, etag, match_condition):
        if self.stale:
            raise CosmosAccessConditionFailedError(status_code=412, message="stale")
        return {**body, "_etag": "e2", "_rid": "r", "_ts": 1}


def test_get_by_email_returns_none_when_missing():
    assert CosmosUserRepository(FakeContainer()).get_by_email("x@example.com") is None


def test_get_by_email_queries_its_own_partition_and_maps_document():
    container = FakeContainer([{**to_document(USER), "_etag": "e1"}])
    assert CosmosUserRepository(container).get_by_email(USER.email) == USER
    assert container.partition_key == USER.email


def test_get_by_email_defaults_favorites_to_empty_for_legacy_documents():
    document = {k: v for k, v in to_document(USER).items() if k != "favorites"}
    container = FakeContainer([{**document, "_etag": "e1"}])
    assert CosmosUserRepository(container).get_by_email(USER.email).favorites == []


def test_create_and_replace_round_trip_the_user_with_favorites():
    user = User(**{**USER.__dict__, "favorites": ["torta", "croissant"]})
    repository = CosmosUserRepository(FakeContainer())
    assert repository.create(user) == user
    assert repository.replace(user) == User(**{**user.__dict__, "etag": "e2"})


def test_replace_maps_412_to_concurrency_conflict():
    with pytest.raises(ConcurrencyConflictError):
        CosmosUserRepository(FakeContainer(stale=True)).replace(USER)


def test_create_maps_409_to_conflict():
    with pytest.raises(ConflictError):
        CosmosUserRepository(FakeContainer(exists=True)).create(USER)
