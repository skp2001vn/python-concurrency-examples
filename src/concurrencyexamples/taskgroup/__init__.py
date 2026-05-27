"""Run checkout checks concurrently before returning a decision.

Use `asyncio.TaskGroup` to treat related async checks as one structured unit of
work.
"""

from concurrencyexamples.taskgroup.checks import CheckoutChecks

__all__ = ["CheckoutChecks"]
