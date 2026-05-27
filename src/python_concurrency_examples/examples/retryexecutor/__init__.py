"""Retry unreliable partner API calls across worker threads.

Use `concurrent.futures.ThreadPoolExecutor` to run independent tasks
concurrently while each task owns its retry attempts.
"""

from python_concurrency_examples.examples.retryexecutor.executor import (
    RetryExecutor,
    RetryResult,
)

__all__ = ["RetryExecutor", "RetryResult"]
