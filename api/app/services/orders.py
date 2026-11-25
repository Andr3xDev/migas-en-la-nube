import logging
import secrets
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone

from app.domain.errors import ConflictError, NotFoundError, RuleViolationError
from app.domain.models import Order, OrderItem, Product, StockDecrement
from app.ports.repositories import OrderRepository, ProductRepository
from app.services.retry import retry_on_conflict

logger = logging.getLogger(__name__)

CANCELLED = "cancelled"
ALLOWED_TRANSITIONS = {
    "received": {"preparing", CANCELLED},
    "preparing": {"ready", CANCELLED},
    "ready": {"delivered", CANCELLED},
    "delivered": set(),
    CANCELLED: set(),
}
ORDER_STATUSES = set(ALLOWED_TRANSITIONS)
SHOP_TIMEZONE = timezone(timedelta(hours=-5))
OPENING_TIME = time(6, 0)
CLOSING_TIME = time(20, 0)
# Crockford base32 (no I, L, O, U) so a code read aloud or handwritten stays unambiguous.
CODE_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
CODE_LENGTH = 8


@dataclass
class NewOrderItem:
    product_id: str
    variant_name: str
    quantity: int


@dataclass
class NewOrder:
    customer_name: str
    phone: str
    pickup_time: datetime
    items: list[NewOrderItem]


def generate_code() -> str:
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))


def aggregate_quantities(items: list[NewOrderItem]) -> dict[tuple[str, str], int]:
    quantities: dict[tuple[str, str], int] = defaultdict(int)
    for item in items:
        quantities[(item.product_id, item.variant_name)] += item.quantity
    return quantities


def find_variant(product: Product | None, variant_name: str):
    variants = product.variants if product else []
    variant = next((v for v in variants if v.name == variant_name), None)
    if variant is None:
        raise RuleViolationError(f"Unknown product or variant: {variant_name}")
    return variant


def validate_pickup(pickup: datetime, now: datetime, wait_minutes: int) -> None:
    if pickup.tzinfo is None:
        raise RuleViolationError("pickupTime must include a timezone offset")
    if not OPENING_TIME <= pickup.astimezone(SHOP_TIMEZONE).time() <= CLOSING_TIME:
        raise RuleViolationError("Pickup must be between 06:00 and 20:00")
    if pickup < now:
        raise RuleViolationError("Pickup time is in the past")
    if pickup < now + timedelta(minutes=wait_minutes):
        raise RuleViolationError("Pickup is before the preparation time")


def decrement_product(
    products: ProductRepository, product_id: str, quantities: dict[str, int]
) -> list[StockDecrement]:
    product = products.get(product_id)
    if product is None:
        raise RuleViolationError(f"Unknown product: {product_id}")
    decrements = []
    for variant in product.variants:
        quantity = quantities.get(variant.name, 0)
        if quantity and variant.stock >= quantity:
            variant.stock -= quantity
            decrements.append(StockDecrement(product_id, variant.name, quantity))
    if decrements:
        products.replace(product)
    return decrements


def decrement_with_retry(
    products: ProductRepository, product_id: str, quantities: dict[tuple[str, str], int]
) -> list[StockDecrement]:
    wanted = {variant: qty for (pid, variant), qty in quantities.items() if pid == product_id}
    return retry_on_conflict(lambda: decrement_product(products, product_id, wanted))


def restore_stock(products: ProductRepository, decrements: list[StockDecrement]) -> list[Exception]:
    def restore(decrement: StockDecrement) -> None:
        product = products.get(decrement.product_id)
        # The product or variant may have been deleted since the order was placed.
        variant = (
            next((v for v in product.variants if v.name == decrement.variant_name), None)
            if product
            else None
        )
        if variant is None:
            return
        variant.stock += decrement.quantity
        products.replace(product)

    failures: list[Exception] = []
    for decrement in decrements:
        try:
            retry_on_conflict(lambda d=decrement: restore(d))
        except Exception as failure:
            failures.append(failure)
    return failures


def create_order(
    products: ProductRepository,
    orders: OrderRepository,
    order: NewOrder,
    *,
    now: datetime,
    user_id: str | None = None,
) -> Order:
    quantities = aggregate_quantities(order.items)
    catalog = {pid: products.get(pid) for pid, _ in quantities}
    lines: list[OrderItem] = []
    wait_minutes = 0
    for (product_id, variant_name), quantity in quantities.items():
        product = catalog[product_id]
        variant = find_variant(product, variant_name)
        if variant.stock < quantity:
            wait_minutes = max(wait_minutes, product.prep_minutes)
        lines.append(OrderItem(product_id, product.name, variant_name, variant.price, quantity))
    pickup = order.pickup_time
    validate_pickup(pickup, now, wait_minutes)

    applied: list[StockDecrement] = []
    try:
        for product_id in sorted(catalog):
            # A lost stock race leaves the item made-to-order; prep time is not re-checked.
            applied += decrement_with_retry(products, product_id, quantities)
        local_pickup = pickup.astimezone(SHOP_TIMEZONE)
        return orders.create(
            Order(
                id=generate_code(),
                customer_name=order.customer_name,
                phone=order.phone,
                pickup_time=local_pickup,
                pickup_date=local_pickup.date().isoformat(),
                items=lines,
                total=sum(line.unit_price * line.quantity for line in lines),
                user_id=user_id,
                stock_decrements=applied,
            )
        )
    except Exception as error:
        for failure in restore_stock(products, applied):
            error.add_note(f"Stock restore failed: {failure!r}")
        raise


def list_by_date(orders: OrderRepository, pickup_date: str) -> list[Order]:
    return orders.list_by_date(pickup_date)


def change_status(
    orders: OrderRepository,
    products: ProductRepository,
    order_id: str,
    pickup_date: str,
    status: str,
) -> Order:
    order = orders.get(order_id, pickup_date)
    if order is None:
        raise NotFoundError(order_id)
    if status not in ORDER_STATUSES:
        raise RuleViolationError(f"Unknown status: {status}")
    if status not in ALLOWED_TRANSITIONS[order.status]:
        raise ConflictError(f"Cannot change status from {order.status} to {status}")
    order.status = status
    updated = orders.replace(order)
    # Status is committed before restoring on purpose (a retry would restore twice);
    # a restore failure is only logged and needs a manual stock fix.
    if status == CANCELLED:
        for failure in restore_stock(products, updated.stock_decrements):
            logger.warning("Stock restore failed for order %s: %r", order_id, failure)
    return updated
