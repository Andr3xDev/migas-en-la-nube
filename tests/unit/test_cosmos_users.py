import pytest
from azure.cosmos.exceptions import CosmosResourceExistsError

from app.adapters.cosmos.users import CosmosUserRepository, to_document
from app.domain.errors import ConflictError
from app.domain.models import User

USER = User(id="u1", email="ana@example.com", password_hash="hash", role="admin", etag="e1")


class FakeContainer:
    def __init__(self, documents=(), exists=False):
        self.documents = list(documents)
        self.exists = exists
        self.partition_key = None

    def query_items(self, query, parameters, partition_key):
        self.partition_key = partition_key
        return iter(self.documents)

    def create_item(self, body):
        if self.exists:
            raise CosmosResourceExistsError(status_code=409, message="exists")
        return {**body, "_etag": "e1", "_rid": "r", "_ts": 1}


def test_get_by_email_returns_none_when_missing():
    assert CosmosUserRepository(FakeContainer()).get_by_email("x@example.com") is None


def test_get_by_email_queries_its_own_partition_and_maps_document():
    container = FakeContainer([{**to_document(USER), "_etag": "e1"}])
    assert CosmosUserRepository(container).get_by_email(USER.email) == USER
    assert container.partition_key == USER.email


def test_create_round_trips_and_maps_409_to_conflict():
    assert CosmosUserRepository(FakeContainer()).create(USER) == USER
    with pytest.raises(ConflictError):
        CosmosUserRepository(FakeContainer(exists=True)).create(USER)
