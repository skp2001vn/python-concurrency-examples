"""Unit tests for the ratelimiter example.

The example models request threads calling a third-party API with a concurrency
quota. The tests verify caller-facing behavior: invalid limits are rejected,
permits are returned after success or failure, callers can time out, and
concurrent callers never exceed the configured in-flight limit.
"""

import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event, Lock

from concurrency_examples.ratelimiter import ApiRateLimiter


class ApiRateLimiterTest(unittest.TestCase):
    """ApiRateLimiterTest verifies the public permit behavior."""

    # Verifies that callers must choose a positive in-flight limit.
    def test_rejects_invalid_limit(self) -> None:
        with self.assertRaises(ValueError):
            ApiRateLimiter(max_in_flight=0)

    # Verifies that a permit is returned after a successful API call.
    def test_releases_permit_after_success(self) -> None:
        limiter = ApiRateLimiter(max_in_flight=1)

        with limiter.acquire(timeout=0):
            pass

        with limiter.acquire(timeout=0):
            pass

    # Verifies that a permit is returned after a failed API call.
    def test_releases_permit_after_failure(self) -> None:
        limiter = ApiRateLimiter(max_in_flight=1)

        with self.assertRaises(RuntimeError):
            with limiter.acquire(timeout=0):
                raise RuntimeError("api call failed")

        with limiter.acquire(timeout=0):
            pass

    # Verifies that callers can time out when all permits are held.
    def test_times_out_when_permits_are_unavailable(self) -> None:
        limiter = ApiRateLimiter(max_in_flight=1)

        with limiter.acquire(timeout=0):
            with self.assertRaises(TimeoutError):
                with limiter.acquire(timeout=0):
                    self.fail("permit should not be acquired")

    # Verifies that concurrent API calls never exceed the in-flight limit.
    def test_limits_concurrent_api_calls(self) -> None:
        max_in_flight = 3
        call_count = 12
        limiter = ApiRateLimiter(max_in_flight=max_in_flight)
        ready = Barrier(call_count + 1)
        first_wave_ready = Event()
        release_calls = Event()
        active_lock = Lock()
        active_count = 0
        peak_active_count = 0

        def call_api() -> bool:
            nonlocal active_count, peak_active_count
            ready.wait(timeout=1)
            with limiter.acquire(timeout=1):
                with active_lock:
                    active_count += 1
                    peak_active_count = max(peak_active_count, active_count)
                    if active_count > max_in_flight:
                        raise AssertionError("too many active API calls")
                    if active_count == max_in_flight:
                        first_wave_ready.set()

                try:
                    if not release_calls.wait(timeout=1):
                        raise AssertionError("timed out waiting to release API calls")
                    return True
                finally:
                    with active_lock:
                        active_count -= 1

        with ThreadPoolExecutor(max_workers=call_count) as executor:
            futures = [executor.submit(call_api) for _ in range(call_count)]
            ready.wait(timeout=1)
            if not first_wave_ready.wait(timeout=1):
                release_calls.set()
                self.fail("timed out waiting for first API call wave")

            with active_lock:
                self.assertEqual(active_count, max_in_flight)
                self.assertEqual(peak_active_count, max_in_flight)

            release_calls.set()
            self.assertEqual(
                [future.result(timeout=1) for future in futures],
                [True] * call_count,
            )

        self.assertEqual(peak_active_count, max_in_flight)


if __name__ == "__main__":
    unittest.main()
