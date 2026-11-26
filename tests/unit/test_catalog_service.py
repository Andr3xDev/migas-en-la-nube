import pytest

from app.adapters.memory.products import MemoryProductRepository
from app.domain.models import Product, Variant
from app.services.catalog import (
    IN_STOCK,
    MADE_TO_ORDER,
    compute_availability,
    seed_products,
)
from scripts.seed_products import load_products


def make_product(product_id: str = "croissant", name: str = "Croissant") -> Product:
    return Product(
        id=product_id,
        name=name,
        category="bakery",
        description="Buttery",
        image_url=None,
        prep_minutes=90,
        variants=[Variant(name="Single", price=6000, stock=5)],
    )


@pytest.mark.parametrize(
    ("stock", "status", "ready_minutes"),
    [(5, IN_STOCK, None), (0, MADE_TO_ORDER, 90)],
    ids=["in stock", "made to order"],
)
def test_availability_follows_stock(stock, status, ready_minutes):
    availability = compute_availability(
        Variant(name="Single", price=6000, stock=stock), prep_minutes=90
    )

    assert availability.status == status
    assert availability.ready_minutes == ready_minutes


def test_seed_twice_keeps_product_count():
    repo = MemoryProductRepository()
    items = [make_product("a"), make_product("b")]

    seed_products(repo, items)
    seed_products(repo, items)

    assert len(repo.list_all()) == 2


def test_seed_keeps_edited_product_values():
    repo = MemoryProductRepository()
    seed_products(repo, [make_product("a")])
    edited = repo.get("a")
    edited.name = "Edited by admin"
    repo.replace(edited)

    seed_products(repo, [make_product("a")])

    assert repo.get("a").name == "Edited by admin"


def test_seed_file_has_unique_ids_and_valid_variants():
    products = load_products()

    assert len({product.id for product in products}) == len(products)
    for product in products:
        assert product.variants
        for variant in product.variants:
            assert isinstance(variant.price, int) and variant.price >= 0
