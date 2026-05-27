"""Unit tests for the barrierdeployment example.

The example models deployment workers preparing independent steps before
switching traffic together. The tests verify caller-facing behavior: invalid
worker counts and step names are rejected, workers block until everyone arrives,
all workers proceed once ready, timeouts break the gate, and reset makes it
usable for a later deployment attempt.
"""

import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, BrokenBarrierError, Event

from concurrency_examples.barrierdeployment import DeploymentGate


class DeploymentGateTest(unittest.TestCase):
    """DeploymentGateTest verifies the public deployment gate behavior."""

    # Verifies that a deployment needs at least two coordinated workers.
    def test_rejects_too_few_workers(self) -> None:
        with self.assertRaises(ValueError):
            DeploymentGate(required_workers=1)

    # Verifies that every worker must identify its deployment step.
    def test_rejects_blank_step_name(self) -> None:
        gate = DeploymentGate(required_workers=2)

        with self.assertRaises(ValueError):
            gate.wait_until_ready("", timeout=0)

    # Verifies that workers wait until all deployment steps are ready.
    def test_workers_block_until_everyone_arrives(self) -> None:
        gate = DeploymentGate(required_workers=2)
        first_worker_waiting = Event()
        release_second_worker = Event()

        def prepare_assets() -> int:
            first_worker_waiting.set()
            return gate.wait_until_ready("assets", timeout=1)

        def prepare_cache() -> int:
            if not release_second_worker.wait(timeout=1):
                raise AssertionError("timed out waiting to release cache worker")
            return gate.wait_until_ready("cache", timeout=1)

        with ThreadPoolExecutor(max_workers=2) as executor:
            first = executor.submit(prepare_assets)
            second = executor.submit(prepare_cache)

            try:
                self.assertTrue(first_worker_waiting.wait(timeout=1))
                self.assertFalse(first.done())
            finally:
                release_second_worker.set()

            results = {first.result(timeout=1), second.result(timeout=1)}

        self.assertEqual(results, {0, 1})
        self.assertFalse(gate.is_broken())

    # Verifies that all workers proceed once every deployment step is ready.
    def test_releases_all_workers_when_everyone_is_ready(self) -> None:
        worker_count = 3
        gate = DeploymentGate(required_workers=worker_count)
        local_ready = Barrier(worker_count + 1)

        def prepare_step(index: int) -> int:
            local_ready.wait(timeout=1)
            return gate.wait_until_ready(f"step-{index}", timeout=1)

        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            futures = [
                executor.submit(prepare_step, index)
                for index in range(worker_count)
            ]
            local_ready.wait(timeout=1)
            results = {future.result(timeout=1) for future in futures}

        self.assertEqual(results, {0, 1, 2})

    # Verifies that a timeout breaks the deployment gate for all workers.
    def test_timeout_breaks_gate(self) -> None:
        gate = DeploymentGate(required_workers=2)

        with self.assertRaises(BrokenBarrierError):
            gate.wait_until_ready("assets", timeout=0)

        self.assertTrue(gate.is_broken())
        with self.assertRaises(BrokenBarrierError):
            gate.wait_until_ready("cache", timeout=0)

    # Verifies that reset makes a broken gate usable for another attempt.
    def test_reset_allows_later_deployment_attempt(self) -> None:
        gate = DeploymentGate(required_workers=2)

        with self.assertRaises(BrokenBarrierError):
            gate.wait_until_ready("assets", timeout=0)
        gate.reset()

        with ThreadPoolExecutor(max_workers=2) as executor:
            first = executor.submit(gate.wait_until_ready, "assets", 1)
            second = executor.submit(gate.wait_until_ready, "cache", 1)
            results = {first.result(timeout=1), second.result(timeout=1)}

        self.assertEqual(results, {0, 1})
        self.assertFalse(gate.is_broken())


if __name__ == "__main__":
    unittest.main()
