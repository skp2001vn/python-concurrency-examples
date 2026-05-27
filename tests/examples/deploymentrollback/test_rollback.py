"""Unit tests for the deploymentrollback example.

The example models deployment workers registering rollback actions and rollback
workers executing them during cleanup. The tests verify caller-facing behavior:
invalid actions are rejected, rollback runs in last-in-first-out order, empty
stacks report no work, concurrent workers can register actions safely, and
rollback workers execute each action at most once.
"""

import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

from python_concurrency_examples.examples.deploymentrollback import (
    DeploymentRollback,
    RollbackAction,
)


class DeploymentRollbackTest(unittest.TestCase):
    """DeploymentRollbackTest verifies the public rollback stack behavior."""

    # Verifies that rollback action IDs must be non-empty.
    def test_rejects_empty_action_id(self) -> None:
        with self.assertRaises(ValueError):
            RollbackAction(
                action_id="",
                resource_id="service-a",
                description="Restore service",
            )

    # Verifies that rollback resource IDs must be non-empty.
    def test_rejects_empty_resource_id(self) -> None:
        with self.assertRaises(ValueError):
            RollbackAction(
                action_id="rollback-1",
                resource_id="",
                description="Restore service",
            )

    # Verifies that rollback descriptions must be non-empty.
    def test_rejects_empty_description(self) -> None:
        with self.assertRaises(ValueError):
            RollbackAction(
                action_id="rollback-1",
                resource_id="service-a",
                description="",
            )

    # Verifies that rollback actions are executed in reverse registration order.
    def test_runs_actions_in_lifo_order(self) -> None:
        rollback = DeploymentRollback()
        executed_action_ids: list[str] = []

        rollback.register(self.action("database"))
        rollback.register(self.action("config"))
        rollback.register(self.action("traffic"))

        completed_count = rollback.drain(
            lambda action: executed_action_ids.append(action.action_id)
        )

        rollback.join()
        self.assertEqual(completed_count, 3)
        self.assertEqual(executed_action_ids, ["traffic", "config", "database"])
        self.assertEqual(rollback.size(), 0)

    # Verifies that empty rollback stacks report no available work.
    def test_run_next_returns_false_when_empty(self) -> None:
        rollback = DeploymentRollback()

        self.assertFalse(rollback.run_next(lambda action: None))

    # Verifies that task accounting completes even when a rollback handler fails.
    def test_run_next_marks_task_done_when_handler_fails(self) -> None:
        rollback = DeploymentRollback()
        rollback.register(self.action("database"))

        with self.assertRaises(RuntimeError):
            rollback.run_next(self.raise_rollback_error)

        rollback.join()
        self.assertEqual(rollback.size(), 0)

    # Verifies that deployment worker threads can register all actions safely.
    def test_concurrent_workers_register_all_actions(self) -> None:
        action_count = 50
        rollback = DeploymentRollback()

        def register_action(index: int) -> None:
            rollback.register(self.action(f"action-{index}"))

        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [
                executor.submit(register_action, index)
                for index in range(action_count)
            ]
            for future in futures:
                future.result(timeout=1)

        executed_action_ids: set[str] = set()
        rollback.drain(lambda action: executed_action_ids.add(action.action_id))
        rollback.join()

        self.assertEqual(
            executed_action_ids,
            {f"action-{index}" for index in range(action_count)},
        )
        self.assertEqual(rollback.size(), 0)

    # Verifies that concurrent rollback workers execute each action at most once.
    def test_concurrent_rollback_workers_run_each_action_once(self) -> None:
        action_count = 80
        worker_count = 6
        rollback = DeploymentRollback()
        executed_action_ids: list[str] = []
        executed_lock = Lock()

        for index in range(action_count):
            rollback.register(self.action(f"action-{index}"))

        def run_actions() -> None:
            def record(action: RollbackAction) -> None:
                with executed_lock:
                    executed_action_ids.append(action.action_id)

            while rollback.run_next(record):
                pass

        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            futures = [executor.submit(run_actions) for _ in range(worker_count)]
            for future in futures:
                future.result(timeout=1)

        rollback.join()
        self.assertEqual(len(executed_action_ids), action_count)
        self.assertEqual(
            set(executed_action_ids),
            {f"action-{index}" for index in range(action_count)},
        )
        self.assertEqual(len(set(executed_action_ids)), action_count)

    def action(self, action_id: str) -> RollbackAction:
        """Create one valid rollback action for tests."""
        return RollbackAction(
            action_id=action_id,
            resource_id=f"resource-{action_id}",
            description=f"Rollback {action_id}",
        )

    def raise_rollback_error(self, action: RollbackAction) -> None:
        """Raise a fixed error from a simulated rollback handler."""
        raise RuntimeError(f"{action.action_id} failed")


if __name__ == "__main__":
    unittest.main()
