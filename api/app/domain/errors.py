INVALID_CREDENTIALS = "Invalid credentials"
EMAIL_ALREADY_REGISTERED = "Email already registered"


class NotFoundError(Exception):
    """Resource does not exist (HTTP 404)."""


class ConflictError(Exception):
    """Request clashes with current state (HTTP 409)."""


class RuleViolationError(Exception):
    """Business rule rejected the request (HTTP 422)."""


class AuthenticationError(Exception):
    """Credentials or token rejected (HTTP 401)."""


class ConcurrencyConflictError(Exception):
    """Stale ETag on write; services decide whether to retry."""
