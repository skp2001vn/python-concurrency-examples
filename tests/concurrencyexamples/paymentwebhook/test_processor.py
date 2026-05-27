"""Unit tests for the paymentwebhook example.

The example models duplicate webhook delivery from a payment processor. The
tests verify caller-facing behavior: invalid events are rejected, duplicate
event IDs are ignored, concurrent duplicates apply once, and concurrent unique
events all update totals exactly once.
"""

import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from concurrencyexamples.paymentwebhook import (
    PaymentSummary,
    PaymentWebhookProcessor,
)


class PaymentWebhookProcessorTest(unittest.TestCase):
    """PaymentWebhookProcessorTest verifies the public webhook behavior."""

    # Verifies that webhook event IDs must be non-empty.
    def test_rejects_blank_event_id(self) -> None:
        processor = PaymentWebhookProcessor()

        with self.assertRaises(ValueError):
            processor.process("", amount_cents=100)

    # Verifies that payment amounts must be positive.
    def test_rejects_non_positive_amount(self) -> None:
        processor = PaymentWebhookProcessor()

        with self.assertRaises(ValueError):
            processor.process("evt-1", amount_cents=0)

    # Verifies that a new payment event updates the totals once.
    def test_processes_new_event(self) -> None:
        processor = PaymentWebhookProcessor()

        self.assertTrue(processor.process("evt-1", amount_cents=2500))

        self.assertEqual(
            processor.summary(),
            PaymentSummary(processed_events=1, total_cents=2500),
        )
        self.assertEqual(processor.processed_event_ids(), frozenset({"evt-1"}))

    # Verifies that duplicate payment events are ignored.
    def test_ignores_duplicate_event_id(self) -> None:
        processor = PaymentWebhookProcessor()

        self.assertTrue(processor.process("evt-1", amount_cents=2500))
        self.assertFalse(processor.process("evt-1", amount_cents=2500))

        self.assertEqual(
            processor.summary(),
            PaymentSummary(processed_events=1, total_cents=2500),
        )

    # Verifies that concurrent duplicate deliveries apply only once.
    def test_concurrent_duplicate_deliveries_apply_once(self) -> None:
        delivery_count = 50
        processor = PaymentWebhookProcessor()
        ready = Barrier(delivery_count + 1)

        def deliver_duplicate() -> bool:
            ready.wait(timeout=1)
            return processor.process("evt-1", amount_cents=2500)

        with ThreadPoolExecutor(max_workers=delivery_count) as executor:
            futures = [executor.submit(deliver_duplicate) for _ in range(delivery_count)]
            ready.wait(timeout=1)
            results = [future.result(timeout=1) for future in futures]

        self.assertEqual(results.count(True), 1)
        self.assertEqual(results.count(False), delivery_count - 1)
        self.assertEqual(
            processor.summary(),
            PaymentSummary(processed_events=1, total_cents=2500),
        )

    # Verifies that concurrent unique events all update totals exactly once.
    def test_concurrent_unique_deliveries_all_apply(self) -> None:
        delivery_count = 25
        processor = PaymentWebhookProcessor()
        ready = Barrier(delivery_count + 1)

        def deliver_unique(index: int) -> bool:
            ready.wait(timeout=1)
            return processor.process(f"evt-{index}", amount_cents=100)

        with ThreadPoolExecutor(max_workers=delivery_count) as executor:
            futures = [
                executor.submit(deliver_unique, index)
                for index in range(delivery_count)
            ]
            ready.wait(timeout=1)
            results = [future.result(timeout=1) for future in futures]

        self.assertEqual(results.count(True), delivery_count)
        self.assertEqual(
            processor.summary(),
            PaymentSummary(
                processed_events=delivery_count,
                total_cents=delivery_count * 100,
            ),
        )


if __name__ == "__main__":
    unittest.main()
