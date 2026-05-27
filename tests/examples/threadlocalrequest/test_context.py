"""Unit tests for the threadlocalrequest example.

The example models request IDs used for logging, auditing, or tracing in worker
threads. The tests verify caller-facing behavior: blank IDs are rejected,
request IDs can be set and cleared, and each thread sees only its own request
context.
"""

import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from python_concurrency_examples.examples.threadlocalrequest import RequestContext


class RequestContextTest(unittest.TestCase):
    """RequestContextTest verifies the public thread-local behavior."""

    # Verifies that a new thread context starts without a request ID.
    def test_starts_without_request_id(self) -> None:
        context = RequestContext()

        self.assertIsNone(context.get_request_id())

    # Verifies that request IDs must be non-empty.
    def test_rejects_blank_request_id(self) -> None:
        context = RequestContext()

        with self.assertRaises(ValueError):
            context.set_request_id("")

    # Verifies that one thread can set, read, and clear its request ID.
    def test_sets_and_clears_request_id(self) -> None:
        context = RequestContext()

        context.set_request_id("req-1")
        self.assertEqual(context.get_request_id(), "req-1")

        context.clear()

        self.assertIsNone(context.get_request_id())

    # Verifies that worker threads do not share request IDs with each other.
    def test_request_ids_are_isolated_per_thread(self) -> None:
        worker_count = 6
        context = RequestContext()
        ready = Barrier(worker_count + 1)
        release = Barrier(worker_count + 1)

        def handle_request(index: int) -> tuple[str, str | None]:
            request_id = f"req-{index}"
            context.set_request_id(request_id)
            ready.wait(timeout=1)
            observed = context.get_request_id()
            release.wait(timeout=1)
            return request_id, observed

        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            futures = [
                executor.submit(handle_request, index)
                for index in range(worker_count)
            ]
            ready.wait(timeout=1)
            self.assertIsNone(context.get_request_id())
            release.wait(timeout=1)
            results = [future.result(timeout=1) for future in futures]

        self.assertEqual(
            set(results),
            {(f"req-{index}", f"req-{index}") for index in range(worker_count)},
        )

    # Verifies that clearing one thread does not affect another thread's context.
    def test_clear_affects_only_current_thread(self) -> None:
        context = RequestContext()
        worker_ready = Barrier(2)
        worker_done = Barrier(2)

        def worker() -> str | None:
            context.set_request_id("worker-req")
            worker_ready.wait(timeout=1)
            worker_done.wait(timeout=1)
            return context.get_request_id()

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(worker)
            worker_ready.wait(timeout=1)

            context.set_request_id("main-req")
            context.clear()
            worker_done.wait(timeout=1)

            self.assertEqual(future.result(timeout=1), "worker-req")

        self.assertIsNone(context.get_request_id())


if __name__ == "__main__":
    unittest.main()
