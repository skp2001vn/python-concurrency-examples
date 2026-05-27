"""Unit tests for the asyncpaymentstatus example.

The example models async checkout requests waiting for payment completion. The
tests verify caller-facing behavior: invalid inputs are rejected, waiters block
until a result is published, many waiters receive the same result, late waiters
return immediately, timeouts are raised, and the first completion wins.
"""

import asyncio
import unittest

from concurrency_examples.asyncpaymentstatus import (
    AsyncPaymentStatus,
    PaymentResult,
)


class AsyncPaymentStatusTest(unittest.IsolatedAsyncioTestCase):
    """AsyncPaymentStatusTest verifies the public async status behavior."""

    # Verifies that payment IDs must be non-empty for success updates.
    async def test_rejects_empty_payment_id_for_success(self) -> None:
        status = AsyncPaymentStatus()

        with self.assertRaises(ValueError):
            await status.mark_succeeded("")

    # Verifies that payment IDs must be non-empty for waiters.
    async def test_rejects_empty_payment_id_for_wait(self) -> None:
        status = AsyncPaymentStatus()

        with self.assertRaises(ValueError):
            await status.wait_for_result("")

    # Verifies that failure updates must include a caller-facing reason.
    async def test_rejects_empty_failure_reason(self) -> None:
        status = AsyncPaymentStatus()

        with self.assertRaises(ValueError):
            await status.mark_failed("payment-1", reason="")

    # Verifies that wait timeouts cannot be negative.
    async def test_rejects_negative_timeout(self) -> None:
        status = AsyncPaymentStatus()

        with self.assertRaises(ValueError):
            await status.wait_for_result("payment-1", timeout=-1)

    # Verifies that callers can read a success result without waiting later.
    async def test_marks_payment_succeeded(self) -> None:
        status = AsyncPaymentStatus()

        self.assertTrue(await status.mark_succeeded("payment-1"))

        expected = PaymentResult(payment_id="payment-1", outcome="succeeded")
        self.assertEqual(status.result_for("payment-1"), expected)
        self.assertEqual(await status.wait_for_result("payment-1"), expected)

    # Verifies that callers can read a failure result without waiting later.
    async def test_marks_payment_failed(self) -> None:
        status = AsyncPaymentStatus()

        self.assertTrue(await status.mark_failed("payment-1", reason="card declined"))

        expected = PaymentResult(
            payment_id="payment-1",
            outcome="failed",
            reason="card declined",
        )
        self.assertEqual(status.result_for("payment-1"), expected)
        self.assertEqual(await status.wait_for_result("payment-1"), expected)

    # Verifies that a waiter blocks until the payment result is published.
    async def test_waiter_blocks_until_result_is_published(self) -> None:
        status = AsyncPaymentStatus()
        waiter = asyncio.create_task(status.wait_for_result("payment-1"))

        await asyncio.sleep(0)
        self.assertFalse(waiter.done())

        await status.mark_succeeded("payment-1")

        self.assertEqual(
            await asyncio.wait_for(waiter, timeout=1),
            PaymentResult(payment_id="payment-1", outcome="succeeded"),
        )

    # Verifies that one completion wakes every waiter for the same payment.
    async def test_completion_wakes_all_waiters(self) -> None:
        waiter_count = 10
        status = AsyncPaymentStatus()
        waiters = [
            asyncio.create_task(status.wait_for_result("payment-1"))
            for _ in range(waiter_count)
        ]

        await asyncio.sleep(0)
        await status.mark_failed("payment-1", reason="insufficient funds")
        results = await asyncio.wait_for(asyncio.gather(*waiters), timeout=1)

        self.assertEqual(
            results,
            [
                PaymentResult(
                    payment_id="payment-1",
                    outcome="failed",
                    reason="insufficient funds",
                )
                for _ in range(waiter_count)
            ],
        )

    # Verifies that waiters arriving after completion return immediately.
    async def test_late_waiter_returns_existing_result(self) -> None:
        status = AsyncPaymentStatus()
        await status.mark_succeeded("payment-1")

        result = await asyncio.wait_for(
            status.wait_for_result("payment-1"),
            timeout=1,
        )

        self.assertEqual(
            result,
            PaymentResult(payment_id="payment-1", outcome="succeeded"),
        )

    # Verifies that waiting callers can time out without changing payment state.
    async def test_wait_for_result_times_out(self) -> None:
        status = AsyncPaymentStatus()

        with self.assertRaises(TimeoutError):
            await status.wait_for_result("payment-1", timeout=0.01)

        self.assertIsNone(status.result_for("payment-1"))

    # Verifies that the first completion wins for a payment.
    async def test_first_completion_wins(self) -> None:
        status = AsyncPaymentStatus()

        self.assertTrue(await status.mark_succeeded("payment-1"))
        self.assertFalse(await status.mark_failed("payment-1", reason="too late"))

        self.assertEqual(
            await status.wait_for_result("payment-1"),
            PaymentResult(payment_id="payment-1", outcome="succeeded"),
        )


if __name__ == "__main__":
    unittest.main()
