from dataclasses import dataclass
from typing import Protocol

from app.domain.models import CUSTOMER_ROLE, User


@dataclass(frozen=True)
class Principal:
    user_id: str
    email: str
    role: str


class AuthProvider(Protocol):
    def register(self, email: str, password: str, role: str = CUSTOMER_ROLE) -> User: ...

    def ensure_admin(self, email: str, password: str) -> User: ...

    def login(self, email: str, password: str) -> str: ...

    def verify_token(self, token: str) -> Principal: ...
