"""Coordinate deployment workers before switching traffic.

The business logic is a deployment workflow: workers prepare independent steps
such as assets, cache warmup, and dependency checks, but no worker should switch
traffic until every required worker reaches the readiness point.

The example uses `threading.Barrier` because all deployment workers must
rendezvous before any of them continue. If a worker times out, the barrier is
broken so the deployment can fail instead of partially switching traffic.
"""

from threading import Barrier


class DeploymentGate:
    """DeploymentGate releases prepared workers at the same readiness point.

    The gate is safe for concurrent use by the configured worker threads.
    Workers call `wait_until_ready()` after their local preparation finishes,
    and all waiting workers are released together once every worker arrives.
    """

    def __init__(self, required_workers: int) -> None:
        """Create a deployment gate for the required worker count."""
        if required_workers < 2:
            raise ValueError("required_workers must be at least two")

        self._barrier = Barrier(required_workers)

    def wait_until_ready(self, step_name: str, timeout: float | None = None) -> int:
        """Wait for every deployment worker to become ready."""
        if not step_name:
            raise ValueError("step_name must not be empty")

        return self._barrier.wait(timeout=timeout)

    def reset(self) -> None:
        """Reset a broken gate so the deployment can be attempted again."""
        self._barrier.reset()

    def is_broken(self) -> bool:
        """Return whether a timeout or reset has broken the current gate."""
        return self._barrier.broken
