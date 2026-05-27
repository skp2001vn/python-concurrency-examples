"""Run checkout checks concurrently before returning a decision.

Use `asyncio.TaskGroup` to treat related async checks as one structured unit of
work.
"""

from concurrency_examples.taskgroup.checks import CheckoutChecks

__all__ = ["CheckoutChecks"]
