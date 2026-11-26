from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Response

from app.api.deps import (
    get_image_store,
    get_order_repository,
    get_product_repository,
    require_role,
)
from app.api.routes.orders import to_response as order_to_response
from app.api.routes.products import to_response as product_to_response
from app.api.schemas import (
    AdminOrderResponse,
    ImageUploadRequest,
    ImageUploadResponse,
    ProductRequest,
    ProductResponse,
    ProductUpdateRequest,
    StatusRequest,
)
from app.core.settings import Settings, get_settings
from app.domain.models import ADMIN_ROLE, Order, Variant
from app.ports.images import ImageStore
from app.ports.repositories import OrderRepository, ProductRepository
from app.services import catalog
from app.services import orders as orders_service

router = APIRouter(prefix="/api/admin", dependencies=[Depends(require_role(ADMIN_ROLE))])

Products = Annotated[ProductRepository, Depends(get_product_repository)]
Orders = Annotated[OrderRepository, Depends(get_order_repository)]
Images = Annotated[ImageStore, Depends(get_image_store)]
AppSettings = Annotated[Settings, Depends(get_settings)]


def to_product_data(request: ProductRequest) -> catalog.ProductData:
    return catalog.ProductData(
        name=request.name,
        category=request.category,
        description=request.description,
        image_url=request.image_url,
        prep_minutes=request.prep_minutes,
        variants=[Variant(**vars(variant)) for variant in request.variants],
    )


def to_admin_response(order: Order) -> AdminOrderResponse:
    return AdminOrderResponse(
        **vars(order_to_response(order)),
        customer_name=order.customer_name,
        phone=order.phone,
        pickup_date=order.pickup_date,
    )


@router.post("/products", status_code=201)
def create_product(
    request: ProductRequest, products: Products, settings: AppSettings
) -> ProductResponse:
    product = catalog.create_product(
        products, to_product_data(request), images_container_url=settings.images_container_url
    )
    return product_to_response(product)


@router.put("/products/{product_id}")
def update_product(
    product_id: str, request: ProductUpdateRequest, products: Products, settings: AppSettings
) -> ProductResponse:
    product = catalog.update_product(
        products,
        product_id,
        to_product_data(request),
        etag=request.etag,
        images_container_url=settings.images_container_url,
    )
    return product_to_response(product)


@router.delete("/products/{product_id}", status_code=204)
def delete_product(product_id: str, products: Products, images: Images) -> Response:
    catalog.delete_product(products, images, product_id)
    return Response(status_code=204)


@router.post("/products/{product_id}/image-upload-url")
def create_image_upload(
    product_id: str, request: ImageUploadRequest, products: Products, images: Images
) -> ImageUploadResponse:
    upload = catalog.create_image_upload(products, images, product_id, request.content_type)
    return ImageUploadResponse(**vars(upload))


@router.get("/orders")
def list_orders(
    orders: Orders,
    date: date | None = None,
    scope: Literal["upcoming", "history"] = "upcoming",
) -> list[AdminOrderResponse]:
    if date is not None:
        found = orders_service.list_by_date(orders, date.isoformat())
    elif scope == "history":
        found = orders_service.list_history(orders)
    else:
        found = orders_service.list_upcoming(orders)
    return [to_admin_response(order) for order in found]


@router.patch("/orders/{order_id}/status")
def change_order_status(
    order_id: str, date: date, request: StatusRequest, orders: Orders, products: Products
) -> AdminOrderResponse:
    order = orders_service.change_status(
        orders, products, order_id, date.isoformat(), request.status
    )
    return to_admin_response(order)
