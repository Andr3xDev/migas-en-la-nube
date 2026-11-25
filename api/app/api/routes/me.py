from typing import Annotated

from fastapi import APIRouter, Depends, Response

from app.api.deps import (
    current_user,
    get_order_repository,
    get_product_repository,
    get_user_repository,
)
from app.api.routes.orders import to_response as order_to_response
from app.api.routes.products import to_response as product_to_response
from app.api.schemas import OrderResponse, ProductResponse
from app.ports.auth import Principal
from app.ports.repositories import OrderRepository, ProductRepository, UserRepository
from app.services import accounts

router = APIRouter(prefix="/api", dependencies=[Depends(current_user)])

Caller = Annotated[Principal, Depends(current_user)]
Orders = Annotated[OrderRepository, Depends(get_order_repository)]
Products = Annotated[ProductRepository, Depends(get_product_repository)]
Users = Annotated[UserRepository, Depends(get_user_repository)]


@router.get("/me/orders")
def list_my_orders(caller: Caller, orders: Orders) -> list[OrderResponse]:
    return [order_to_response(order) for order in accounts.list_user_orders(orders, caller.user_id)]


@router.get("/me/favorites")
def list_my_favorites(caller: Caller, users: Users) -> list[str]:
    return accounts.list_favorites(users, caller.email)


@router.put("/me/favorites/{product_id}", status_code=204)
def add_my_favorite(product_id: str, caller: Caller, users: Users, products: Products) -> Response:
    accounts.add_favorite(users, products, caller.email, product_id)
    return Response(status_code=204)


@router.delete("/me/favorites/{product_id}", status_code=204)
def remove_my_favorite(product_id: str, caller: Caller, users: Users) -> Response:
    accounts.remove_favorite(users, caller.email, product_id)
    return Response(status_code=204)


@router.get("/me/top-products")
def list_my_top_products(
    caller: Caller, orders: Orders, products: Products
) -> list[ProductResponse]:
    return [
        product_to_response(product)
        for product in accounts.top_products(orders, products, caller.user_id)
    ]
