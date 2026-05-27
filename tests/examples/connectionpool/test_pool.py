"""Unit tests for the connectionpool example.

The example models request handlers leasing a limited set of database or API
connections. The tests verify caller-facing behavior: empty pools are rejected,
connections are returned after success or failure, checkout can time out, and
concurrent request threads never use more connections than the pool owns.
"""

import unittest
from concurrent.futures import ThreadPoolExecutor
from queue import Empty
from threading import Barrier, Event, Lock

from python_concurrency_examples.examples.connectionpool import ConnectionPool


class ConnectionPoolTest(unittest.TestCase):
    """ConnectionPoolTest verifies the public leasing behavior."""

    # Verifies that callers must provide at least one reusable connection.
    def test_rejects_empty_connection_list(self) -> None:
        with self.assertRaises(ValueError):
            ConnectionPool[str]([])

    # Verifies that checkout returns an available connection.
    def test_checkout_returns_connection(self) -> None:
        pool = ConnectionPool(["conn-1"])

        with pool.checkout(timeout=0) as connection:
            self.assertEqual(connection, "conn-1")
            self.assertEqual(pool.available_count(), 0)

        self.assertEqual(pool.available_count(), 1)

    # Verifies that a successful request returns its connection to the pool.
    def test_returns_connection_after_success(self) -> None:
        pool = ConnectionPool(["conn-1"])

        with pool.checkout(timeout=0):
            pass

        with pool.checkout(timeout=0) as connection:
            self.assertEqual(connection, "conn-1")

    # Verifies that a failed request still returns its connection to the pool.
    def test_returns_connection_after_failure(self) -> None:
        pool = ConnectionPool(["conn-1"])

        with self.assertRaises(RuntimeError):
            with pool.checkout(timeout=0):
                raise RuntimeError("request failed")

        with pool.checkout(timeout=0) as connection:
            self.assertEqual(connection, "conn-1")

    # Verifies that callers can time out when all connections are leased.
    def test_checkout_times_out_when_all_connections_are_leased(self) -> None:
        pool = ConnectionPool(["conn-1"])

        with pool.checkout(timeout=0):
            with self.assertRaises(Empty):
                with pool.checkout(timeout=0):
                    self.fail("checkout should not succeed")

    # Verifies that concurrent requests never lease the same connection at once.
    def test_concurrent_requests_do_not_share_leased_connections(self) -> None:
        connections = ["conn-1", "conn-2", "conn-3"]
        request_count = 12
        pool = ConnectionPool(connections)
        ready = Barrier(request_count + 1)
        first_wave_ready = Event()
        release_requests = Event()
        active_lock = Lock()
        active_connections: set[str] = set()
        peak_active_count = 0

        def use_connection() -> bool:
            nonlocal peak_active_count
            ready.wait(timeout=1)
            with pool.checkout(timeout=1) as connection:
                with active_lock:
                    if connection in active_connections:
                        raise AssertionError("connection leased twice")
                    active_connections.add(connection)
                    peak_active_count = max(
                        peak_active_count,
                        len(active_connections),
                    )
                    if len(active_connections) == len(connections):
                        first_wave_ready.set()

                try:
                    if not release_requests.wait(timeout=1):
                        raise AssertionError("timed out waiting to release requests")
                    return True
                finally:
                    with active_lock:
                        active_connections.remove(connection)

        with ThreadPoolExecutor(max_workers=request_count) as executor:
            futures = [executor.submit(use_connection) for _ in range(request_count)]
            ready.wait(timeout=1)
            if not first_wave_ready.wait(timeout=1):
                release_requests.set()
                self.fail("timed out waiting for first connection wave")

            with active_lock:
                self.assertEqual(len(active_connections), len(connections))
                self.assertEqual(peak_active_count, len(connections))

            release_requests.set()
            self.assertEqual(
                [future.result(timeout=1) for future in futures],
                [True] * request_count,
            )

        self.assertEqual(pool.available_count(), len(connections))


if __name__ == "__main__":
    unittest.main()
