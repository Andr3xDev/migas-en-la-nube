import pytest

from app.core.retry import MAX_CONFLICT_ATTEMPTS, retry_on_conflict
from app.domain.errors import ConcurrencyConflictError, ConflictError


def failing_then(result, failures: int):
    calls = []

    def operation():
        calls.append(1)
        if len(calls) <= failures:
            raise ConcurrencyConflictError("stale")
        return result

    return operation, calls


def test_retry_when_first_attempt_succeeds_returns_result_once():
    operation, calls = failing_then("ok", 0)

    assert retry_on_conflict(operation) == "ok"
    assert len(calls) == 1


def test_retry_when_conflict_then_success_returns_result():
    operation, calls = failing_then("ok", 1)

    assert retry_on_conflict(operation) == "ok"
    assert len(calls) == 2


def test_retry_when_every_attempt_conflicts_raises_conflict_error():
    operation, calls = failing_then("never", 100)

    with pytest.raises(ConflictError):
        retry_on_conflict(operation)
    assert len(calls) == MAX_CONFLICT_ATTEMPTS == 5


def test_retry_when_other_error_propagates_without_retrying():
    calls = []

    def operation():
        calls.append(1)
        raise ValueError("boom")

    with pytest.raises(ValueError):
        retry_on_conflict(operation)
    assert len(calls) == 1
