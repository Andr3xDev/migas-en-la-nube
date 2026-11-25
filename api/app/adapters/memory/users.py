from copy import deepcopy
from uuid import uuid4

from app.domain.errors import (
    EMAIL_ALREADY_REGISTERED,
    ConcurrencyConflictError,
    ConflictError,
    NotFoundError,
)
from app.domain.models import User


class MemoryUserRepository:
    def __init__(self) -> None:
        self._users: dict[str, User] = {}

    def get_by_email(self, email: str) -> User | None:
        user = next((u for u in self._users.values() if u.email == email), None)
        return deepcopy(user)

    def create(self, user: User) -> User:
        if user.id in self._users or any(u.email == user.email for u in self._users.values()):
            raise ConflictError(EMAIL_ALREADY_REGISTERED)
        return self._store(user)

    def replace(self, user: User) -> User:
        current = self._users.get(user.id)
        if current is None:
            raise NotFoundError(user.id)
        if current.etag != user.etag:
            raise ConcurrencyConflictError(user.id)
        return self._store(user)

    def _store(self, user: User) -> User:
        stored = deepcopy(user)
        stored.etag = uuid4().hex
        self._users[stored.id] = stored
        return deepcopy(stored)
