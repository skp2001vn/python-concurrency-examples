"""Register deployment rollback actions from worker threads.

Use `queue.LifoQueue` for thread-safe last-in-first-out cleanup.
"""

from concurrency_examples.deploymentrollback.rollback import (
    DeploymentRollback,
    RollbackAction,
)

__all__ = ["DeploymentRollback", "RollbackAction"]
