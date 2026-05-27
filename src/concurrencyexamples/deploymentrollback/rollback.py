"""Register deployment rollback actions from worker threads.

The business logic is a deployment workflow: several worker threads perform
setup steps, and each successful step registers a rollback action. If a later
step fails, rollback workers execute registered actions in reverse order.

The example uses `queue.LifoQueue` because producers can register rollback
actions safely from multiple threads while the rollback coordinator drains the
most recently registered action first. This preserves stack-style cleanup
without manually combining a list and a lock.
"""

from collections.abc import Callable
from dataclasses import dataclass
from queue import Empty, LifoQueue


@dataclass(frozen=True, slots=True)
class RollbackAction:
    """RollbackAction describes one deployment cleanup step.

    Attributes:
        action_id: Stable identifier for the rollback action.
        resource_id: Deployment resource affected by the action.
        description: Caller-facing summary of the cleanup to run.
    """

    action_id: str
    resource_id: str
    description: str

    def __post_init__(self) -> None:
        """Validate action fields required for rollback coordination."""
        if not self.action_id:
            raise ValueError("action_id must not be empty")
        if not self.resource_id:
            raise ValueError("resource_id must not be empty")
        if not self.description:
            raise ValueError("description must not be empty")


class DeploymentRollback:
    """DeploymentRollback coordinates reverse-order cleanup actions.

    The rollback stack is safe for concurrent use by many threads. Deployment
    workers register completed-step rollback actions, and rollback workers run
    each registered action at most once in last-in-first-out order.
    """

    def __init__(self) -> None:
        """Create an empty rollback stack."""
        self._queue: LifoQueue[RollbackAction] = LifoQueue()

    def register(self, action: RollbackAction) -> None:
        """Register one rollback action for later reverse-order execution."""
        self._queue.put(action)

    def run_next(self, handler: Callable[[RollbackAction], None]) -> bool:
        """Run the next rollback action and return whether one was available."""
        try:
            action = self._queue.get(block=False)
        except Empty:
            return False

        try:
            handler(action)
        finally:
            self._queue.task_done()

        return True

    def drain(self, handler: Callable[[RollbackAction], None]) -> int:
        """Run all currently registered rollback actions and return the count."""
        completed_count = 0
        while self.run_next(handler):
            completed_count += 1
        return completed_count

    def join(self) -> None:
        """Block until all claimed rollback actions have been marked done."""
        self._queue.join()

    def size(self) -> int:
        """Return the approximate number of registered rollback actions."""
        return self._queue.qsize()
