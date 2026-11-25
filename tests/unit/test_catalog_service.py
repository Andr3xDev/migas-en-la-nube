import pytest

from app.adapters.memory.products import MemoryProductRepository
from app.domain.errors import NotFoundError
from app.domain.models import Product, Variant
from app.services.catalog import (
    IN_STOCK,
    MADE_TO_ORDER,
    compute_availability,
    get_product,
    list_products,
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


def test_availability_when_stock_positive_is_in_stock():
    availability = compute_availability(
        Variant(name="Single", price=6000, stock=5), prep_minutes=90
    )

    assert availability.status == IN_STOCK
    assert availability.ready_minutes is None


def test_availability_when_stock_zero_is_made_to_order_with_prep_minutes():
    availability = compute_availability(
        Variant(name="Single", price=6000, stock=0), prep_minutes=90
    )

    assert availability.status == MADE_TO_ORDER
    assert availability.ready_minutes == 90


def test_list_products_returns_all_stored_products():
    repo = MemoryProductRepository()
    repo.create(make_product("a"))
    repo.create(make_product("b"))

    assert {p.id for p in list_products(repo)} == {"a", "b"}


def test_get_product_when_missing_raises_not_found():
    with pytest.raises(NotFoundError):
        get_product(MemoryProductRepository(), "missing")


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
