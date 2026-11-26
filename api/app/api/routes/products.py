from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_product_repository
from app.api.schemas import AvailabilityResponse, ProductResponse, VariantResponse
from app.domain.models import Product
from app.ports.repositories import ProductRepository
from app.services import catalog

router = APIRouter(prefix="/api")

Repository = Annotated[ProductRepository, Depends(get_product_repository)]


def to_response(product: Product) -> ProductResponse:
    return ProductResponse(
        id=product.id,
        name=product.name,
        category=product.category,
        description=product.description,
        image_url=product.image_url,
        prep_minutes=product.prep_minutes,
        etag=product.etag,
        variants=[
            VariantResponse(
                name=variant.name,
                price=variant.price,
                stock=variant.stock,
                availability=AvailabilityResponse(
                    **vars(catalog.compute_availability(variant, product.prep_minutes))
                ),
            )
            for variant in product.variants
        ],
    )


@router.get("/products")
def list_products(repo: Repository) -> list[ProductResponse]:
    return [to_response(product) for product in catalog.list_products(repo)]


@router.get("/products/{product_id}")
def get_product(product_id: str, repo: Repository) -> ProductResponse:
    return to_response(catalog.get_product(repo, product_id))
