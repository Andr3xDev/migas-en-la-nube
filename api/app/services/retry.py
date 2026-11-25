from collections.abc import Callable
from typing import TypeVar

from app.domain.errors import ConcurrencyConflictError, ConflictError

T = TypeVar("T")

MAX_STOCK_ATTEMPTS = 5


def retry_on_conflict(operation: Callable[[], T], attempts: int = MAX_STOCK_ATTEMPTS) -> T:
    for _ in range(attempts):
        try:
            return operation()
        except ConcurrencyConflictError:
            continue
    raise ConflictError("Too many concurrent updates, try again")
