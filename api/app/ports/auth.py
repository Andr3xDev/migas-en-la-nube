from dataclasses import dataclass
from typing import Protocol

from app.domain.models import User


@dataclass(frozen=True)
class Principal:
    user_id: str
    email: str
    role: str


class AuthProvider(Protocol):
    def register(self, email: str, password: str, role: str = "customer") -> User: ...

    def login(self, email: str, password: str) -> str: ...

    def verify_token(self, token: str) -> Principal: ...
