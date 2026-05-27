"""Unit tests for the requesttracker example.

The example models graceful service shutdown while requests are still in
flight. The tests verify caller-facing behavior: active requests are counted,
counts are cleaned up on success or failure, shutdown rejects new requests, and
shutdown waiters are released when active handlers finish.
"""

import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event

from python_concurrency_examples.examples.requesttracker import (
    RequestTracker,
    ShutdownStartedError,
)


class RequestTrackerTest(unittest.TestCase):
    """RequestTrackerTest verifies the public shutdown behavior."""

    # Verifies that a request context increments and decrements active count.
    def test_tracks_active_request_context(self) -> None:
        tracker = RequestTracker()

        with tracker.track_request():
            self.assertEqual(tracker.active_requests(), 1)

        self.assertEqual(tracker.active_requests(), 0)

    # Verifies that active count is cleaned up when a request handler fails.
    def test_tracks_failed_request_cleanup(self) -> None:
        tracker = RequestTracker()

        with self.assertRaises(RuntimeError):
            with tracker.track_request():
                raise RuntimeError("handler failed")

        self.assertEqual(tracker.active_requests(), 0)

    # Verifies that shutdown stops new request handlers from starting.
    def test_rejects_new_requests_after_shutdown_begins(self) -> None:
        tracker = RequestTracker()

        tracker.begin_shutdown()

        self.assertTrue(tracker.is_shutting_down())
        with self.assertRaises(ShutdownStartedError):
            with tracker.track_request():
                self.fail("request should not start")

    # Verifies that shutdown can time out while requests are still active.
    def test_wait_until_drained_returns_false_on_timeout(self) -> None:
        tracker = RequestTracker()

        with tracker.track_request():
            tracker.begin_shutdown()

            self.assertFalse(tracker.wait_until_drained(timeout=0))

    # Verifies that shutdown waiters return immediately when no requests are active.
    def test_wait_until_drained_returns_true_when_already_drained(self) -> None:
        tracker = RequestTracker()

        tracker.begin_shutdown()

        self.assertTrue(tracker.wait_until_drained(timeout=0))

    # Verifies that shutdown waits until existing request threads finish.
    def test_waiter_returns_after_active_requests_finish(self) -> None:
        request_count = 4
        tracker = RequestTracker()
        requests_started = Barrier(request_count + 1)
        release_requests = Event()

        def handle_request() -> bool:
            with tracker.track_request():
                requests_started.wait(timeout=1)
                if not release_requests.wait(timeout=1):
                    raise AssertionError("timed out waiting to release request")
                return True

        with ThreadPoolExecutor(max_workers=request_count + 1) as executor:
            futures = [executor.submit(handle_request) for _ in range(request_count)]
            requests_started.wait(timeout=1)
            tracker.begin_shutdown()
            waiter = executor.submit(tracker.wait_until_drained, 1)

            self.assertEqual(tracker.active_requests(), request_count)
            with self.assertRaises(ShutdownStartedError):
                with tracker.track_request():
                    self.fail("request should not start")

            release_requests.set()
            self.assertTrue(waiter.result(timeout=1))
            self.assertEqual(
                [future.result(timeout=1) for future in futures],
                [True] * request_count,
            )

        self.assertEqual(tracker.active_requests(), 0)


if __name__ == "__main__":
    unittest.main()
