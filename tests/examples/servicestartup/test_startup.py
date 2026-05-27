"""Unit tests for the servicestartup example.

The example models request handlers waiting for startup work before accepting
traffic. The tests verify caller-facing behavior: readiness starts false,
waiting can time out, readiness is idempotent, and many request threads are
released once startup completes.
"""

import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from python_concurrency_examples.examples.servicestartup import ServiceStartup


class ServiceStartupTest(unittest.TestCase):
    """ServiceStartupTest verifies the public readiness behavior."""

    # Verifies that a new service starts in the not-ready state.
    def test_starts_not_ready(self) -> None:
        startup = ServiceStartup()

        self.assertFalse(startup.is_ready())

    # Verifies that callers can time out instead of accepting requests too soon.
    def test_wait_returns_false_before_startup_completes(self) -> None:
        startup = ServiceStartup()

        self.assertFalse(startup.wait_until_ready(timeout=0))

    # Verifies that marking ready releases later callers immediately.
    def test_wait_returns_true_after_startup_completes(self) -> None:
        startup = ServiceStartup()

        startup.mark_ready()

        self.assertTrue(startup.is_ready())
        self.assertTrue(startup.wait_until_ready(timeout=0))

    # Verifies that marking startup ready more than once is harmless.
    def test_mark_ready_is_idempotent(self) -> None:
        startup = ServiceStartup()

        startup.mark_ready()
        startup.mark_ready()

        self.assertTrue(startup.is_ready())

    # Verifies that request threads wait until startup broadcasts readiness.
    def test_releases_waiting_request_threads_when_ready(self) -> None:
        request_count = 8
        startup = ServiceStartup()
        requests_waiting = Barrier(request_count + 1)

        def handle_request() -> bool:
            requests_waiting.wait(timeout=1)
            return startup.wait_until_ready(timeout=1)

        with ThreadPoolExecutor(max_workers=request_count) as executor:
            futures = [executor.submit(handle_request) for _ in range(request_count)]
            requests_waiting.wait(timeout=1)

            self.assertFalse(startup.is_ready())
            startup.mark_ready()

            self.assertEqual(
                [future.result(timeout=1) for future in futures],
                [True] * request_count,
            )


if __name__ == "__main__":
    unittest.main()
