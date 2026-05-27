"""Unit tests for the taskgroup example.

The example models async checkout checks that must finish before a request can
return a decision. The tests verify caller-facing behavior: invalid check sets
are rejected, successful checks return results, checks run concurrently, and a
failed check cancels sibling checks through structured concurrency.
"""

import asyncio
import unittest

from concurrencyexamples.taskgroup import CheckoutChecks


class CheckoutChecksTest(unittest.IsolatedAsyncioTestCase):
    """CheckoutChecksTest verifies the public async check behavior."""

    # Verifies that callers must provide at least one named check.
    async def test_rejects_empty_check_set(self) -> None:
        with self.assertRaises(ValueError):
            CheckoutChecks[str]({})

    # Verifies that check names must be non-empty.
    async def test_rejects_blank_check_name(self) -> None:
        with self.assertRaises(ValueError):
            CheckoutChecks[str]({"": self.pass_check})

    # Verifies that successful checks return their results by business name.
    async def test_returns_successful_check_results(self) -> None:
        checks = CheckoutChecks(
            {
                "fraud": lambda: self.return_check("clear"),
                "inventory": lambda: self.return_check("available"),
            },
        )

        results = await checks.run()

        self.assertEqual(
            results,
            {
                "fraud": "clear",
                "inventory": "available",
            },
        )

    # Verifies that independent checks run concurrently, not one after another.
    async def test_runs_checks_concurrently(self) -> None:
        check_count = 3
        active_count = 0
        peak_active_count = 0
        active_lock = asyncio.Lock()
        all_started = asyncio.Event()
        release_checks = asyncio.Event()

        async def tracked_check(name: str) -> str:
            nonlocal active_count, peak_active_count
            async with active_lock:
                active_count += 1
                peak_active_count = max(peak_active_count, active_count)
                if active_count == check_count:
                    all_started.set()

            try:
                await release_checks.wait()
                return f"{name}:ok"
            finally:
                async with active_lock:
                    active_count -= 1

        checks = CheckoutChecks(
            {
                "fraud": lambda: tracked_check("fraud"),
                "inventory": lambda: tracked_check("inventory"),
                "customer": lambda: tracked_check("customer"),
            },
        )

        run_task = asyncio.create_task(checks.run())
        await asyncio.wait_for(all_started.wait(), timeout=1)
        self.assertEqual(peak_active_count, check_count)

        release_checks.set()
        results = await asyncio.wait_for(run_task, timeout=1)

        self.assertEqual(
            results,
            {
                "fraud": "fraud:ok",
                "inventory": "inventory:ok",
                "customer": "customer:ok",
            },
        )

    # Verifies that a failed required check cancels sibling checks.
    async def test_failed_check_cancels_sibling_checks(self) -> None:
        slow_check_started = asyncio.Event()
        slow_check_cancelled = asyncio.Event()

        async def slow_inventory_check() -> str:
            slow_check_started.set()
            try:
                await asyncio.sleep(10)
                return "available"
            except asyncio.CancelledError:
                slow_check_cancelled.set()
                raise

        async def failing_fraud_check() -> str:
            await slow_check_started.wait()
            raise RuntimeError("fraud check failed")

        checks = CheckoutChecks(
            {
                "inventory": slow_inventory_check,
                "fraud": failing_fraud_check,
            },
        )

        with self.assertRaises(ExceptionGroup) as caught:
            await checks.run()

        self.assertTrue(slow_check_cancelled.is_set())
        self.assertEqual(len(caught.exception.exceptions), 1)
        self.assertIsInstance(caught.exception.exceptions[0], RuntimeError)

    async def pass_check(self) -> str:
        """Return a fixed successful check result."""
        return "ok"

    async def return_check(self, result: str) -> str:
        """Return the provided check result."""
        return result


if __name__ == "__main__":
    unittest.main()
