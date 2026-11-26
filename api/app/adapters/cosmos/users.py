from typing import Any

from azure.core import MatchConditions
from azure.cosmos.container import ContainerProxy
from azure.cosmos.exceptions import (
    CosmosAccessConditionFailedError,
    CosmosResourceExistsError,
    CosmosResourceNotFoundError,
)

from app.domain.errors import (
    EMAIL_ALREADY_REGISTERED,
    ConcurrencyConflictError,
    ConflictError,
    NotFoundError,
)
from app.domain.models import User

CONTAINER_NAME = "users"


def to_document(user: User) -> dict[str, Any]:
    return {
        "id": user.id,
        "email": user.email,
        "passwordHash": user.password_hash,
        "role": user.role,
        "favorites": user.favorites,
    }


def from_document(document: dict[str, Any]) -> User:
    return User(
        id=document["id"],
        email=document["email"],
        password_hash=document["passwordHash"],
        role=document["role"],
        etag=document["_etag"],
        favorites=list(document.get("favorites", [])),
    )


class CosmosUserRepository:
    def __init__(self, container: ContainerProxy) -> None:
        self._container = container

    def get_by_email(self, email: str) -> User | None:
        documents = list(
            self._container.query_items(
                "SELECT * FROM c WHERE c.email = @email",
                parameters=[{"name": "@email", "value": email}],
                partition_key=email,
            )
        )
        return from_document(documents[0]) if documents else None

    def create(self, user: User) -> User:
        try:
            created = self._container.create_item(to_document(user))
        except CosmosResourceExistsError as error:
            raise ConflictError(EMAIL_ALREADY_REGISTERED) from error
        return from_document(created)

    def replace(self, user: User) -> User:
        try:
            replaced = self._container.replace_item(
                user.id,
                to_document(user),
                etag=user.etag,
                match_condition=MatchConditions.IfNotModified,
            )
        except CosmosAccessConditionFailedError as error:
            raise ConcurrencyConflictError(user.id) from error
        except CosmosResourceNotFoundError as error:
            raise NotFoundError(user.id) from error
        return from_document(replaced)
