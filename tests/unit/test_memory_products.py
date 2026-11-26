import pytest

from app.adapters.memory.products import MemoryProductRepository
from app.domain.errors import ConcurrencyConflictError
from app.domain.models import Product, Variant


def make_product(product_id: str = "croissant", category: str = "bakery") -> Product:
    return Product(
        id=product_id,
        name="Croissant",
        category=category,
        description="Buttery",
        image_url=None,
        prep_minutes=90,
        variants=[Variant(name="Single", price=6000, stock=5)],
    )


def test_replace_with_fresh_etag_saves_changes_and_rotates_etag():
    repo = MemoryProductRepository()
    repo.create(make_product())
    loaded = repo.get("croissant")
    old_etag = loaded.etag
    loaded.name = "Almond croissant"

    replaced = repo.replace(loaded)

    assert repo.get("croissant").name == "Almond croissant"
    assert replaced.etag != old_etag


def test_replace_with_stale_etag_raises_concurrency_conflict():
    repo = MemoryProductRepository()
    repo.create(make_product())
    first = repo.get("croissant")
    second = repo.get("croissant")
    repo.replace(first)

    with pytest.raises(ConcurrencyConflictError):
        repo.replace(second)


def test_get_returns_copy_so_unsaved_edits_do_not_leak():
    repo = MemoryProductRepository()
    repo.create(make_product())
    repo.get("croissant").name = "Mutated"

    assert repo.get("croissant").name == "Croissant"
