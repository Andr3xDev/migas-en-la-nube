import pytest

from app.adapters.memory.products import MemoryProductRepository
from app.api.deps import get_product_repository
from app.domain.models import Product, Variant


@pytest.fixture
def repo(client):
    repository = MemoryProductRepository()
    client.app.dependency_overrides[get_product_repository] = lambda: repository
    return repository


def make_product(product_id: str, stock: int = 5):
    return Product(
        id=product_id,
        name="Croissant",
        category="bakery",
        description="Buttery",
        image_url=None,
        prep_minutes=90,
        variants=[Variant(name="Single", price=6000, stock=stock)],
    )


def test_list_products_without_token_returns_public_shape(client, repo):
    created = repo.create(make_product("croissant"))

    response = client.get("/api/products")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": "croissant",
            "name": "Croissant",
            "category": "bakery",
            "description": "Buttery",
            "imageUrl": None,
            "prepMinutes": 90,
            "etag": created.etag,
            "variants": [
                {
                    "name": "Single",
                    "price": 6000,
                    "stock": 5,
                    "availability": {"status": "in stock", "readyMinutes": None},
                }
            ],
        }
    ]


def test_get_product_when_made_to_order_exposes_ready_time(client, repo):
    repo.create(make_product("croissant", stock=0))

    body = client.get("/api/products/croissant").json()

    assert body["variants"][0]["availability"] == {"status": "made to order", "readyMinutes": 90}


def test_get_product_when_unknown_returns_404(client, repo):
    assert client.get("/api/products/missing").status_code == 404
