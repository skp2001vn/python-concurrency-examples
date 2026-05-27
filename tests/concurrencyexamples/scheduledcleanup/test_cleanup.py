"""Unit tests for the scheduledcleanup example.

The example models background maintenance work such as removing expired
sessions or temporary files. The tests verify caller-facing behavior: invalid
intervals are rejected, the worker starts once, stop is safe before start,
cleanup runs in the background, errors are captured, and shutdown joins the
worker thread.
"""

import unittest
from threading import Event, Lock

from concurrencyexamples.scheduledcleanup import ScheduledCleanup


class ScheduledCleanupTest(unittest.TestCase):
    """ScheduledCleanupTest verifies the public worker lifecycle behavior."""

    # Verifies that callers must choose a positive cleanup interval.
    def test_rejects_invalid_interval(self) -> None:
        with self.assertRaises(ValueError):
            ScheduledCleanup(lambda: None, interval=0)

    # Verifies that stopping before start is safe and immediate.
    def test_stop_before_start_returns_true(self) -> None:
        cleanup = ScheduledCleanup(lambda: None, interval=0.01)

        self.assertTrue(cleanup.stop(timeout=0))
        self.assertFalse(cleanup.is_running())

    # Verifies that the cleanup worker can only be started once.
    def test_rejects_double_start(self) -> None:
        cleanup_ran = Event()
        cleanup = ScheduledCleanup(cleanup_ran.set, interval=0.01)
        self.addCleanup(cleanup.stop, 1)

        cleanup.start()

        with self.assertRaises(RuntimeError):
            cleanup.start()

    # Verifies that cleanup work runs in the background thread.
    def test_runs_cleanup_in_background(self) -> None:
        cleanup_ran = Event()
        cleanup = ScheduledCleanup(cleanup_ran.set, interval=0.01)
        self.addCleanup(cleanup.stop, 1)

        cleanup.start()

        self.assertTrue(cleanup.is_running())
        self.assertTrue(cleanup_ran.wait(timeout=1))

    # Verifies that stop wakes the worker and waits for it to exit.
    def test_stop_joins_worker_thread(self) -> None:
        cleanup = ScheduledCleanup(lambda: None, interval=10)
        cleanup.start()

        self.assertTrue(cleanup.stop(timeout=1))

        self.assertFalse(cleanup.is_running())

    # Verifies that cleanup exceptions are captured and the worker keeps running.
    def test_captures_cleanup_errors(self) -> None:
        cleanup_attempted = Event()

        def fail_cleanup() -> None:
            cleanup_attempted.set()
            raise RuntimeError("cleanup failed")

        cleanup = ScheduledCleanup(fail_cleanup, interval=0.01)
        self.addCleanup(cleanup.stop, 1)

        cleanup.start()

        self.assertTrue(cleanup_attempted.wait(timeout=1))
        errors = cleanup.errors()
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], RuntimeError)
        self.assertTrue(cleanup.is_running())

    # Verifies that repeated cleanup runs can update shared maintenance state.
    def test_repeats_cleanup_until_stopped(self) -> None:
        cleanup_count = 0
        cleanup_lock = Lock()
        enough_runs = Event()

        def cleanup_expired_sessions() -> None:
            nonlocal cleanup_count
            with cleanup_lock:
                cleanup_count += 1
                if cleanup_count >= 2:
                    enough_runs.set()

        cleanup = ScheduledCleanup(cleanup_expired_sessions, interval=0.01)
        self.addCleanup(cleanup.stop, 1)

        cleanup.start()

        self.assertTrue(enough_runs.wait(timeout=1))
        self.assertTrue(cleanup.stop(timeout=1))
        with cleanup_lock:
            self.assertGreaterEqual(cleanup_count, 2)


if __name__ == "__main__":
    unittest.main()
