"""Unit tests for the retryexecutor example.

The example models concurrent calls to unreliable partner APIs. The tests
verify caller-facing behavior: invalid limits are rejected, transient failures
are retried, exhausted attempts are reported as failures, and independent tasks
run across worker threads.
"""

import unittest
from threading import Barrier, Lock

from concurrency_examples.retryexecutor import RetryExecutor


class RetryExecutorTest(unittest.TestCase):
    """RetryExecutorTest verifies the public retry behavior."""

    # Verifies that callers must choose positive worker and attempt limits.
    def test_rejects_invalid_limits(self) -> None:
        with self.assertRaises(ValueError):
            RetryExecutor(max_workers=0, max_attempts=1)
        with self.assertRaises(ValueError):
            RetryExecutor(max_workers=1, max_attempts=0)

    # Verifies that callers must provide at least one task with an ID.
    def test_rejects_invalid_tasks(self) -> None:
        executor = RetryExecutor(max_workers=1, max_attempts=1)

        with self.assertRaises(ValueError):
            executor.run_all({})
        with self.assertRaises(ValueError):
            executor.run("", lambda: "ignored")

    # Verifies that a successful task returns its value after one attempt.
    def test_succeeds_on_first_attempt(self) -> None:
        executor = RetryExecutor(max_workers=1, max_attempts=3)

        result = executor.run("partner-a", lambda: "accepted")

        self.assertTrue(result.succeeded)
        self.assertEqual(result.task_id, "partner-a")
        self.assertEqual(result.attempts, 1)
        self.assertEqual(result.value, "accepted")
        self.assertIsNone(result.error)

    # Verifies that transient partner failures are retried until success.
    def test_retries_until_later_attempt_succeeds(self) -> None:
        executor = RetryExecutor(max_workers=1, max_attempts=3)
        attempts = 0

        def flaky_call() -> str:
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise RuntimeError("temporary partner failure")
            return "accepted"

        result = executor.run("partner-a", flaky_call)

        self.assertTrue(result.succeeded)
        self.assertEqual(result.attempts, 3)
        self.assertEqual(result.value, "accepted")

    # Verifies that exhausted attempts return a failed result instead of raising.
    def test_reports_failure_after_attempts_are_exhausted(self) -> None:
        executor = RetryExecutor(max_workers=1, max_attempts=2)

        result = executor.run("partner-a", self.raise_partner_error)

        self.assertFalse(result.succeeded)
        self.assertEqual(result.attempts, 2)
        self.assertIsNone(result.value)
        self.assertIsInstance(result.error, RuntimeError)

    # Verifies that independent partner calls run across worker threads.
    def test_runs_multiple_tasks_concurrently(self) -> None:
        task_count = 3
        executor = RetryExecutor(max_workers=task_count, max_attempts=1)
        ready = Barrier(task_count)
        active_lock = Lock()
        active_count = 0
        peak_active_count = 0

        def partner_call(name: str) -> str:
            nonlocal active_count, peak_active_count
            with active_lock:
                active_count += 1
                peak_active_count = max(peak_active_count, active_count)
            try:
                ready.wait(timeout=1)
                return f"{name}:accepted"
            finally:
                with active_lock:
                    active_count -= 1

        results = executor.run_all(
            {
                "partner-a": lambda: partner_call("partner-a"),
                "partner-b": lambda: partner_call("partner-b"),
                "partner-c": lambda: partner_call("partner-c"),
            },
        )

        self.assertEqual(peak_active_count, task_count)
        self.assertEqual(
            {task_id: result.value for task_id, result in results.items()},
            {
                "partner-a": "partner-a:accepted",
                "partner-b": "partner-b:accepted",
                "partner-c": "partner-c:accepted",
            },
        )
        self.assertTrue(all(result.succeeded for result in results.values()))

    def raise_partner_error(self) -> None:
        """Raise a fixed error from a simulated partner API call."""
        raise RuntimeError("partner unavailable")


if __name__ == "__main__":
    unittest.main()
