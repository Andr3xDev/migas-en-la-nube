from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient

from app.adapters.local_auth import LocalAuthProvider
from app.adapters.memory.orders import MemoryOrderRepository
from app.adapters.memory.products import MemoryProductRepository
from app.adapters.memory.users import MemoryUserRepository
from app.api.deps import (
    get_auth_provider,
    get_order_repository,
    get_product_repository,
    get_user_repository,
)
from app.domain.models import CUSTOMER_ROLE, Product, Variant
from app.main import app

SIGNING_KEY = "route-test-signing-key-32-bytes-min"
PASSWORD = "correct horse"


@dataclass
class Stack:
    auth: LocalAuthProvider
    users: MemoryUserRepository
    orders: MemoryOrderRepository
    products: MemoryProductRepository
    key: str = SIGNING_KEY
    password: str = PASSWORD

    def headers_for(self, email: str, role: str = CUSTOMER_ROLE) -> dict[str, str]:
        self.auth.register(email, PASSWORD, role=role)
        return {"X-Pdc-Token": f"Bearer {self.auth.login(email, PASSWORD)}"}


@pytest.fixture
def client():
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def stack(client):
    """In-memory repos and auth overrides, seeded with one `croissant` product."""
    users = MemoryUserRepository()
    orders = MemoryOrderRepository()
    products = MemoryProductRepository()
    products.create(
        Product(
            "croissant", "Croissant", "bakery", "Buttery", None, 90, [Variant("Single", 6000, 5)]
        )
    )
    auth = LocalAuthProvider(
        users, SIGNING_KEY, login_failure_delay_seconds=0, sleep=lambda _: None
    )
    overrides = client.app.dependency_overrides
    overrides[get_user_repository] = lambda: users
    overrides[get_auth_provider] = lambda: auth
    overrides[get_order_repository] = lambda: orders
    overrides[get_product_repository] = lambda: products
    return Stack(auth, users, orders, products)
