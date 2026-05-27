"""Reserve limited stock during concurrent checkout.

Use `threading.Lock` to protect inventory counts and keep reservations from
overselling available stock.
"""

from python_concurrency_examples.examples.inventoryreservation.inventory import (
    InventoryReservation,
)

__all__ = ["InventoryReservation"]
