from collections import Counter
from itertools import islice

from app.core.retry import retry_on_conflict
from app.domain.errors import NotFoundError
from app.domain.models import Order, Product, User
from app.ports.repositories import OrderRepository, ProductRepository, UserRepository
from app.services.orders import CANCELLED

TOP_PRODUCTS_LIMIT = 3


def list_user_orders(orders: OrderRepository, user_id: str) -> list[Order]:
    return sorted(orders.list_by_user(user_id), key=lambda order: order.pickup_time, reverse=True)


def _get_user(users: UserRepository, email: str) -> User:
    user = users.get_by_email(email)
    if user is None:
        raise NotFoundError(email)
    return user


def add_favorite(
    users: UserRepository, products: ProductRepository, email: str, product_id: str
) -> None:
    if products.get(product_id) is None:
        raise NotFoundError(product_id)

    def attempt() -> None:
        user = _get_user(users, email)
        if product_id not in user.favorites:
            user.favorites.append(product_id)
            users.replace(user)

    retry_on_conflict(attempt)


def remove_favorite(users: UserRepository, email: str, product_id: str) -> None:
    def attempt() -> None:
        user = _get_user(users, email)
        if product_id in user.favorites:
            user.favorites.remove(product_id)
            users.replace(user)

    retry_on_conflict(attempt)


def list_favorites(users: UserRepository, email: str) -> list[str]:
    return list(_get_user(users, email).favorites)


def top_products(
    orders: OrderRepository, products: ProductRepository, user_id: str
) -> list[Product]:
    quantities: Counter[str] = Counter()
    for order in orders.list_by_user(user_id):
        if order.status != CANCELLED:
            for item in order.items:
                quantities[item.product_id] += item.quantity
    ranked = sorted(quantities, key=lambda product_id: (-quantities[product_id], product_id))
    found = (products.get(product_id) for product_id in ranked)
    available = (product for product in found if product is not None)
    return list(islice(available, TOP_PRODUCTS_LIMIT))
