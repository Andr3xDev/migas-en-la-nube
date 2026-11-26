from copy import deepcopy
from uuid import uuid4

from app.domain.errors import ConcurrencyConflictError, ConflictError, NotFoundError
from app.domain.models import Order


class MemoryOrderRepository:
    def __init__(self) -> None:
        self._orders: dict[str, Order] = {}

    def create(self, order: Order) -> Order:
        if order.id in self._orders:
            raise ConflictError(order.id)
        return self._store(order)

    def get(self, order_id: str, pickup_date: str) -> Order | None:
        order = self._orders.get(order_id)
        if order is None or order.pickup_date != pickup_date:
            return None
        return deepcopy(order)

    def replace(self, order: Order) -> Order:
        current = self._orders.get(order.id)
        if current is None:
            raise NotFoundError(order.id)
        if current.etag != order.etag:
            raise ConcurrencyConflictError(order.id)
        return self._store(order)

    def list_by_date(self, pickup_date: str) -> list[Order]:
        matches = [o for o in self._orders.values() if o.pickup_date == pickup_date]
        return [deepcopy(o) for o in sorted(matches, key=lambda o: o.pickup_time)]

    def list_by_statuses(
        self, statuses: list[str], newest_first: bool, limit: int | None = None
    ) -> list[Order]:
        matches = [o for o in self._orders.values() if o.status in statuses]
        ordered = sorted(matches, key=lambda o: o.pickup_time, reverse=newest_first)[:limit]
        return [deepcopy(o) for o in ordered]

    def list_by_user(self, user_id: str) -> list[Order]:
        return [deepcopy(o) for o in self._orders.values() if o.user_id == user_id]

    def _store(self, order: Order) -> Order:
        stored = deepcopy(order)
        stored.etag = uuid4().hex
        self._orders[stored.id] = stored
        return deepcopy(stored)
