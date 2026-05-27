"""Unit tests for the inventoryreservation example.

The example models limited stock during concurrent checkout. The tests verify
caller-facing behavior: invalid stock is rejected, reservations update
availability, insufficient stock is not oversold, and concurrent checkout
threads cannot reserve more than the available inventory.
"""

import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from concurrencyexamples.inventoryreservation import (
    InventoryReservation,
)


class InventoryReservationTest(unittest.TestCase):
    """InventoryReservationTest verifies the public checkout behavior."""

    # Verifies that callers must configure at least one product.
    def test_rejects_empty_inventory(self) -> None:
        with self.assertRaises(ValueError):
            InventoryReservation({})

    # Verifies that initial stock counts cannot be negative.
    def test_rejects_negative_initial_stock(self) -> None:
        with self.assertRaises(ValueError):
            InventoryReservation({"sku-1": -1})

    # Verifies that product IDs must be non-empty strings.
    def test_rejects_blank_product_ids(self) -> None:
        with self.assertRaises(ValueError):
            InventoryReservation({"": 1})

        inventory = InventoryReservation({"sku-1": 1})
        with self.assertRaises(ValueError):
            inventory.reserve("", 1)
        with self.assertRaises(ValueError):
            inventory.available("")

    # Verifies that reservations reduce available stock when enough exists.
    def test_reserves_available_stock(self) -> None:
        inventory = InventoryReservation({"sku-1": 5})

        self.assertTrue(inventory.reserve("sku-1", 3))

        self.assertEqual(inventory.available("sku-1"), 2)
        self.assertEqual(inventory.snapshot(), {"sku-1": 2})

    # Verifies that insufficient stock does not change inventory.
    def test_rejects_reservation_when_stock_is_insufficient(self) -> None:
        inventory = InventoryReservation({"sku-1": 2})

        self.assertFalse(inventory.reserve("sku-1", 3))

        self.assertEqual(inventory.available("sku-1"), 2)

    # Verifies that callers must reserve a positive quantity.
    def test_rejects_non_positive_reservation_quantity(self) -> None:
        inventory = InventoryReservation({"sku-1": 2})

        with self.assertRaises(ValueError):
            inventory.reserve("sku-1", 0)

    # Verifies that callers cannot reserve or inspect unknown products.
    def test_rejects_unknown_product(self) -> None:
        inventory = InventoryReservation({"sku-1": 2})

        with self.assertRaises(KeyError):
            inventory.reserve("missing", 1)
        with self.assertRaises(KeyError):
            inventory.available("missing")

    # Verifies that concurrent checkout threads cannot oversell inventory.
    def test_concurrent_checkout_does_not_oversell_stock(self) -> None:
        stock_count = 25
        checkout_count = 100
        inventory = InventoryReservation({"sku-1": stock_count})
        ready = Barrier(checkout_count + 1)

        def checkout() -> bool:
            ready.wait(timeout=1)
            return inventory.reserve("sku-1", 1)

        with ThreadPoolExecutor(max_workers=checkout_count) as executor:
            futures = [executor.submit(checkout) for _ in range(checkout_count)]
            ready.wait(timeout=1)
            results = [future.result(timeout=1) for future in futures]

        self.assertEqual(results.count(True), stock_count)
        self.assertEqual(results.count(False), checkout_count - stock_count)
        self.assertEqual(inventory.available("sku-1"), 0)


if __name__ == "__main__":
    unittest.main()
