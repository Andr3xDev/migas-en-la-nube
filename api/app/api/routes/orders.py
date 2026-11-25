from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import (
    get_now,
    get_optional_principal,
    get_order_repository,
    get_product_repository,
)
from app.api.schemas import OrderItemResponse, OrderRequest, OrderResponse
from app.domain.models import Order
from app.ports.auth import Principal
from app.ports.repositories import OrderRepository, ProductRepository
from app.services import orders as orders_service

router = APIRouter(prefix="/api")


def to_response(order: Order) -> OrderResponse:
    return OrderResponse(
        code=order.id,
        status=order.status,
        items=[OrderItemResponse(**vars(item)) for item in order.items],
        total=order.total,
        pickup_time=order.pickup_time,
    )


@router.post("/orders", status_code=201)
def create_order(
    request: OrderRequest,
    products: Annotated[ProductRepository, Depends(get_product_repository)],
    orders: Annotated[OrderRepository, Depends(get_order_repository)],
    now: Annotated[datetime, Depends(get_now)],
    principal: Annotated[Principal | None, Depends(get_optional_principal)],
) -> OrderResponse:
    order = orders_service.NewOrder(
        customer_name=request.customer_name,
        phone=request.phone,
        pickup_time=request.pickup_time,
        items=[orders_service.NewOrderItem(**vars(item)) for item in request.items],
    )
    user_id = principal.user_id if principal else None
    return to_response(
        orders_service.create_order(products, orders, order, now=now, user_id=user_id)
    )
