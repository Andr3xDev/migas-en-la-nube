import base64
import hashlib
import hmac
import secrets
import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt

from app.domain.errors import (
    INVALID_CREDENTIALS,
    AuthenticationError,
    ConcurrencyConflictError,
    ConflictError,
)
from app.domain.models import User
from app.ports.auth import Principal
from app.ports.repositories import UserRepository
from app.services.retry import retry_on_conflict

TOKEN_LIFETIME = timedelta(hours=1)
JWT_ALGORITHM = "HS256"
SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_MAX_MEMORY = 128 * 1024 * 1024
SALT_BYTES = 16


def _b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode()


def _scrypt(password: str, salt: bytes, n: int, r: int, p: int) -> bytes:
    # maxmem raised: OpenSSL's 32 MiB default is too tight for n=2**14, r=8.
    return hashlib.scrypt(password.encode(), salt=salt, n=n, r=r, p=p, maxmem=SCRYPT_MAX_MEMORY)


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(SALT_BYTES)
    digest = _scrypt(password, salt, SCRYPT_N, SCRYPT_R, SCRYPT_P)
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, n, r, p, salt, digest = stored.split("$")
        expected = base64.b64decode(digest)
        actual = _scrypt(password, base64.b64decode(salt), int(n), int(r), int(p))
    except ValueError:
        return False
    return hmac.compare_digest(actual, expected)


class LocalAuthProvider:
    def __init__(
        self,
        users: UserRepository,
        jwt_key: str,
        *,
        login_failure_delay_seconds: float = 0.5,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._users = users
        self._jwt_key = jwt_key
        self._delay = login_failure_delay_seconds
        self._sleep = sleep
        # Verified against when the email is unknown, so both failures cost one scrypt.
        self._dummy_hash = hash_password(secrets.token_urlsafe(16))

    # Checked per token operation, not at construction: seeding and guest orders run without a key.
    def _require_jwt_key(self) -> None:
        if not self._jwt_key:
            raise ValueError("jwt_key is required")

    def register(self, email: str, password: str, role: str = "customer") -> User:
        user = User(
            id=uuid4().hex,
            email=email.strip().lower(),
            password_hash=hash_password(password),
            role=role,
        )
        return self._users.create(user)

    def ensure_admin(self, email: str, password: str) -> User:
        def attempt() -> User:
            user = self._users.get_by_email(email.strip().lower())
            if user is None:
                try:
                    return self.register(email, password, role="admin")
                except ConflictError:
                    # Created concurrently after our read; retry re-reads and promotes.
                    raise ConcurrencyConflictError(email) from None
            if user.role == "admin" and verify_password(password, user.password_hash):
                return user
            user.role = "admin"
            user.password_hash = hash_password(password)
            return self._users.replace(user)

        return retry_on_conflict(attempt)

    def login(self, email: str, password: str) -> str:
        user = self._users.get_by_email(email.strip().lower())
        valid = verify_password(password, user.password_hash if user else self._dummy_hash)
        if user is None or not valid:
            self._sleep(self._delay)
            raise AuthenticationError(INVALID_CREDENTIALS)
        self._require_jwt_key()
        now = datetime.now(UTC)
        claims = {
            "sub": user.id,
            "email": user.email,
            "role": user.role,
            "iat": now,
            "exp": now + TOKEN_LIFETIME,
        }
        return jwt.encode(claims, self._jwt_key, algorithm=JWT_ALGORITHM)

    def verify_token(self, token: str) -> Principal:
        self._require_jwt_key()
        try:
            claims = jwt.decode(
                token,
                self._jwt_key,
                algorithms=[JWT_ALGORITHM],
                options={"require": ["exp", "sub"]},
            )
            return Principal(claims["sub"], claims["email"], claims["role"])
        except (jwt.PyJWTError, KeyError):
            raise AuthenticationError(INVALID_CREDENTIALS) from None
