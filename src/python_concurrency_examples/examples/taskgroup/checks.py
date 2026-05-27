"""Run checkout checks concurrently before returning a decision.

The business logic is a checkout decision workflow: a request needs several
independent backend checks, such as fraud, inventory, and customer status,
before it can return a final decision.

The example uses `asyncio.TaskGroup` because the checks are related async tasks
that should succeed or fail as one unit. If one required check fails, the task
group cancels the remaining checks and reports the failure to the caller.
"""

from collections.abc import Awaitable, Callable, Mapping
from asyncio import TaskGroup


class CheckoutChecks[T]:
    """CheckoutChecks runs required async checks for one checkout decision.

    The checks run concurrently in one task group. Callers receive all check
    results when every check succeeds, and receive the task group failure when
    any required check fails.
    """

    def __init__(self, checks: Mapping[str, Callable[[], Awaitable[T]]]) -> None:
        """Create a checkout checker from named async check functions."""
        if not checks:
            raise ValueError("checks must not be empty")
        if any(not check_name for check_name in checks):
            raise ValueError("check names must not be empty")

        self._checks = dict(checks)

    async def run(self) -> dict[str, T]:
        """Run all checks concurrently and return successful results by name."""
        async with TaskGroup() as task_group:
            tasks = {
                check_name: task_group.create_task(check(), name=check_name)
                for check_name, check in self._checks.items()
            }

        return {
            check_name: task.result()
            for check_name, task in tasks.items()
        }
