import logging
from collections.abc import Iterable
from dataclasses import dataclass
from urllib.parse import urlsplit
from uuid import uuid4

from app.domain.errors import NotFoundError, RuleViolationError
from app.domain.models import Product, Variant
from app.ports.images import ImageStore, ImageUpload
from app.ports.repositories import ProductRepository

logger = logging.getLogger(__name__)

IN_STOCK = "in stock"
MADE_TO_ORDER = "made to order"


@dataclass(frozen=True)
class Availability:
    status: str
    ready_minutes: int | None


def compute_availability(variant: Variant, prep_minutes: int) -> Availability:
    if variant.stock > 0:
        return Availability(IN_STOCK, None)
    return Availability(MADE_TO_ORDER, prep_minutes)


def list_products(repo: ProductRepository) -> list[Product]:
    return repo.list_all()


def get_product(repo: ProductRepository, product_id: str) -> Product:
    product = repo.get(product_id)
    if product is None:
        raise NotFoundError(product_id)
    return product


@dataclass
class ProductData:
    name: str
    category: str
    description: str
    image_url: str | None
    prep_minutes: int
    variants: list[Variant]


def validate_product_data(data: ProductData, images_container_url: str) -> None:
    if not data.variants:
        raise RuleViolationError("A product needs at least one variant")
    if any(v.price < 0 or v.stock < 0 for v in data.variants):
        raise RuleViolationError("Price and stock cannot be negative")
    if len({v.name for v in data.variants}) != len(data.variants):
        raise RuleViolationError("Variant names must be unique")
    if data.prep_minutes < 0:
        raise RuleViolationError("prepMinutes cannot be negative")
    if data.image_url is not None:
        image, container = urlsplit(data.image_url), urlsplit(images_container_url)
        if image.netloc != container.netloc or not image.path.startswith(
            f"{container.path.rstrip('/')}/"
        ):
            raise RuleViolationError("imageUrl must point to the images container")


def build_product(product_id: str, data: ProductData, etag: str | None = None) -> Product:
    return Product(product_id, **vars(data), etag=etag)


def create_product(
    repo: ProductRepository, data: ProductData, *, images_container_url: str
) -> Product:
    validate_product_data(data, images_container_url)
    return repo.create(build_product(uuid4().hex, data))


def update_product(
    repo: ProductRepository, product_id: str, data: ProductData, *, images_container_url: str
) -> Product:
    validate_product_data(data, images_container_url)
    current = get_product(repo, product_id)
    updated = build_product(product_id, data, current.etag)
    return repo.move(updated) if updated.category != current.category else repo.replace(updated)


def delete_product(repo: ProductRepository, images: ImageStore, product_id: str) -> None:
    repo.delete(product_id)
    try:
        images.delete_product_images(product_id)
    except Exception as error:
        logger.warning("Image cleanup failed for %s: %s", product_id, type(error).__name__)


def create_image_upload(
    repo: ProductRepository, images: ImageStore, product_id: str, content_type: str
) -> ImageUpload:
    get_product(repo, product_id)
    return images.create_upload(product_id, content_type)


def seed_products(repo: ProductRepository, items: Iterable[Product]) -> None:
    for item in items:
        if repo.get(item.id) is None:
            repo.create(item)
