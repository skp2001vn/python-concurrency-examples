"""Reserve limited stock during concurrent checkout.

The business logic is an inventory reservation workflow: many checkout callers
try to reserve stock for the same products at the same time, and inventory must
never drop below zero.

The example uses `threading.Lock` because each reservation is a check-and-update
operation over shared stock counts. The lock keeps those business rules atomic
for all threads.
"""

from collections.abc import Mapping
from threading import Lock


class InventoryReservation:
    """InventoryReservation protects stock counts for concurrent checkout.

    The inventory state is safe for concurrent use by many threads. Callers can
    reserve available stock, observe current availability, and read a consistent
    snapshot of all product counts.
    """

    def __init__(self, stock: Mapping[str, int]) -> None:
        """Create inventory from product IDs to available stock counts."""
        if not stock:
            raise ValueError("stock must not be empty")
        if any(not product_id for product_id in stock):
            raise ValueError("product IDs must not be empty")
        if any(quantity < 0 for quantity in stock.values()):
            raise ValueError("stock quantities must not be negative")

        self._lock = Lock()
        self._stock = dict(stock)

    def reserve(self, product_id: str, quantity: int) -> bool:
        """Reserve stock if enough is available and return whether it succeeded."""
        if quantity <= 0:
            raise ValueError("quantity must be greater than zero")

        with self._lock:
            available = self._stock_for(product_id)
            if available < quantity:
                return False

            self._stock[product_id] = available - quantity
            return True

    def available(self, product_id: str) -> int:
        """Return the current available stock for one product."""
        with self._lock:
            return self._stock_for(product_id)

    def snapshot(self) -> dict[str, int]:
        """Return a consistent copy of all current stock counts."""
        with self._lock:
            return self._stock.copy()

    def _stock_for(self, product_id: str) -> int:
        if not product_id:
            raise ValueError("product ID must not be empty")
        try:
            return self._stock[product_id]
        except KeyError:
            raise KeyError(f"unknown product ID: {product_id!r}") from None
