"""Unit tests for the atomiccounter example.

The tests verify caller-facing behavior: request outcomes are counted,
concurrent updates do not lose increments, and reset clears state.
"""

import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from time import monotonic, sleep

from python_concurrency_examples.examples.atomiccounter import (
    Metrics,
    Snapshot,
)


class MetricsTest(unittest.TestCase):
    """MetricsTest verifies the public behavior of the metrics collector."""

    # Verifies that callers can count started, successful, and failed requests.
    def test_records_request_outcomes(self) -> None:
        metrics = Metrics()

        self.assertEqual(metrics.start(), 1)
        self.assertEqual(metrics.start(), 2)
        self.assertEqual(metrics.succeed(), 1)
        self.assertEqual(metrics.fail(), 0)

        self.assertEqual(
            metrics.snapshot(),
            Snapshot(
                requests=2,
                success=1,
                failure=1,
                in_flight=0,
                peak_in_flight=2,
            ),
        )

    # Verifies that many threads can update counters without lost increments.
    def test_handles_concurrent_updates(self) -> None:
        callers = 100
        metrics = Metrics()
        release = Event()

        def update(index: int) -> None:
            metrics.start()
            release.wait()
            if index % 2 == 0:
                metrics.succeed()
            else:
                metrics.fail()

        with ThreadPoolExecutor(max_workers=callers) as executor:
            futures = [executor.submit(update, index) for index in range(callers)]
            self.wait_for_in_flight(metrics, callers)
            release.set()
            for future in futures:
                future.result()

        snapshot = metrics.snapshot()
        self.assertEqual(snapshot.requests, callers)
        self.assertEqual(snapshot.success, callers // 2)
        self.assertEqual(snapshot.failure, callers // 2)
        self.assertEqual(snapshot.in_flight, 0)
        self.assertEqual(snapshot.peak_in_flight, callers)

    # Verifies that callers can clear the metric state.
    def test_reset_clears_counters(self) -> None:
        metrics = Metrics()
        metrics.start()
        metrics.succeed()

        metrics.reset()

        self.assertEqual(metrics.snapshot(), Snapshot())

    def wait_for_in_flight(self, metrics: Metrics, want: int) -> None:
        """Wait until the metrics collector reports the wanted active count."""
        deadline = monotonic() + 1
        while monotonic() < deadline:
            if metrics.snapshot().in_flight == want:
                return
            sleep(0.001)
        self.fail(f"timed out waiting for in-flight count {want}")


if __name__ == "__main__":
    unittest.main()
