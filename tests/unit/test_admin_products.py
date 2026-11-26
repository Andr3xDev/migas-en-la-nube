from datetime import UTC, datetime

import pytest

from app.adapters.memory.products import MemoryProductRepository
from app.domain.errors import NotFoundError, RuleViolationError
from app.domain.models import Variant
from app.ports.images import ImageUpload
from app.services import catalog
from app.services.catalog import ProductData

CONTAINER_URL = "https://migasdev.blob.core.windows.net/images"
IMAGE_URL = f"{CONTAINER_URL}/products/p1/a.png"


class FakeImageStore:
    def __init__(self, delete_error: Exception | None = None):
        self.delete_error = delete_error
        self.deleted: list[str] = []
        self.uploads: list[tuple[str, str]] = []

    def create_upload(self, product_id: str, content_type: str) -> ImageUpload:
        self.uploads.append((product_id, content_type))
        return ImageUpload("https://upload", IMAGE_URL, datetime(2026, 11, 25, tzinfo=UTC))

    def delete_product_images(self, product_id: str) -> None:
        self.deleted.append(product_id)
        if self.delete_error:
            raise self.delete_error


def make_data(**overrides) -> ProductData:
    fields = {
        "name": "Croissant",
        "category": "bakery",
        "description": "Buttery",
        "image_url": IMAGE_URL,
        "prep_minutes": 90,
        "variants": [Variant("Single", 6000, 5), Variant("Box", 30000, 0)],
    }
    return ProductData(**{**fields, **overrides})


@pytest.fixture
def products():
    return MemoryProductRepository()


@pytest.fixture
def images():
    return FakeImageStore()


def create(products, data: ProductData | None = None):
    return catalog.create_product(products, data or make_data(), images_container_url=CONTAINER_URL)


def test_create_product_stores_it_under_a_new_id(products):
    created = create(products)

    assert created.id
    assert products.get(created.id).name == "Croissant"
    assert create(products).id != created.id


INVALID_VARIANT_SETS = {
    "no variants": [],
    "negative price": [Variant("A", -1, 1)],
    "negative stock": [Variant("A", 1, -1)],
    "duplicate names": [Variant("A", 1, 1), Variant("A", 2, 2)],
}


@pytest.mark.parametrize("variants", INVALID_VARIANT_SETS.values(), ids=INVALID_VARIANT_SETS)
def test_create_product_with_invalid_variants_raises_and_stores_nothing(products, variants):
    with pytest.raises(RuleViolationError):
        create(products, make_data(variants=variants))

    assert products.list_all() == []


def test_create_product_with_negative_prep_minutes_raises(products):
    with pytest.raises(RuleViolationError):
        create(products, make_data(prep_minutes=-1))


@pytest.mark.parametrize(
    "image_url",
    [
        "https://evil.example.com/images/products/p1/a.png",
        f"{CONTAINER_URL.removesuffix('/images')}/other/a.png",
        f"{CONTAINER_URL}-evil/x.png",
    ],
    ids=["foreign host", "path outside /images/", "sibling prefix /images-evil/"],
)
def test_create_and_update_reject_image_url_outside_images_container(products, image_url):
    product = create(products)

    with pytest.raises(RuleViolationError):
        create(products, make_data(image_url=image_url))
    with pytest.raises(RuleViolationError):
        catalog.update_product(
            products,
            product.id,
            make_data(image_url=image_url),
            etag=product.etag,
            images_container_url=CONTAINER_URL,
        )

    assert len(products.list_all()) == 1
    assert products.get(product.id).image_url == IMAGE_URL


def test_create_product_accepts_null_image_url(products):
    assert create(products, make_data(image_url=None)).image_url is None


def test_update_product_replaces_fields_and_keeps_id(products):
    product = create(products)
    data = make_data(variants=[Variant("Single", 7000, 9)])

    updated = catalog.update_product(
        products, product.id, data, etag=product.etag, images_container_url=CONTAINER_URL
    )

    assert updated.id == product.id
    assert products.get(product.id).variants == [Variant("Single", 7000, 9)]


def test_update_product_changing_category_keeps_one_product_with_same_id(products):
    product = create(products)

    catalog.update_product(
        products,
        product.id,
        make_data(category="drinks"),
        etag=product.etag,
        images_container_url=CONTAINER_URL,
    )

    assert [(p.id, p.category) for p in products.list_all()] == [(product.id, "drinks")]


def test_update_unknown_product_raises_not_found(products):
    with pytest.raises(NotFoundError):
        catalog.update_product(
            products, "nope", make_data(), etag="x", images_container_url=CONTAINER_URL
        )


def test_delete_product_removes_it_and_its_images(products, images):
    product = create(products)

    catalog.delete_product(products, images, product.id)

    assert products.get(product.id) is None
    assert images.deleted == [product.id]


def test_delete_unknown_product_raises_not_found_and_keeps_images(products, images):
    with pytest.raises(NotFoundError):
        catalog.delete_product(products, images, "nope")

    assert images.deleted == []


def test_delete_product_succeeds_and_logs_when_image_cleanup_fails(products, caplog):
    images = FakeImageStore(delete_error=RuntimeError("blob gone"))
    product = create(products)

    catalog.delete_product(products, images, product.id)

    assert products.get(product.id) is None
    assert f"Image cleanup failed for {product.id}" in caplog.text


def test_create_image_upload_for_existing_product_delegates_to_store(products, images):
    product = create(products)

    upload = catalog.create_image_upload(products, images, product.id, "image/png")

    assert upload.image_url == IMAGE_URL
    assert images.uploads == [(product.id, "image/png")]


def test_create_image_upload_for_unknown_product_raises_not_found(products, images):
    with pytest.raises(NotFoundError):
        catalog.create_image_upload(products, images, "nope", "image/png")

    assert images.uploads == []
