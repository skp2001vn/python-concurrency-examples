"""Reserve limited stock during concurrent checkout.

Use `threading.Lock` to protect inventory counts and keep reservations from
overselling available stock.
"""

from concurrencyexamples.inventoryreservation.inventory import (
    InventoryReservation,
)

__all__ = ["InventoryReservation"]
