"""Retry unreliable partner API calls across worker threads.

The business logic is a partner integration workflow: a service calls many
external APIs, some calls fail temporarily, and each failed call should be
retried a limited number of times before being reported as failed.

The example uses `concurrent.futures.ThreadPoolExecutor` because each partner
call is independent and can run in a worker thread. Retry state stays local to
one task, and callers receive a structured result for every submitted call.
"""

from collections.abc import Callable, Mapping
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RetryResult[T]:
    """RetryResult reports the final outcome for one partner API task.

    Attributes:
        task_id: Business identifier for the attempted task.
        attempts: Number of attempts that were made.
        value: Successful return value, or None when the task failed.
        error: Final exception, or None when the task succeeded.
    """

    task_id: str
    attempts: int
    value: T | None = None
    error: Exception | None = None

    @property
    def succeeded(self) -> bool:
        """Return whether the task eventually completed successfully."""
        return self.error is None


class RetryExecutor:
    """RetryExecutor runs retryable partner API calls in worker threads.

    The executor runs independent tasks concurrently. Each task is retried up to
    max_attempts times, and the returned result records the final value or final
    exception without raising task failures to the caller.
    """

    def __init__(self, max_workers: int, max_attempts: int) -> None:
        """Create an executor with worker and retry limits."""
        if max_workers <= 0:
            raise ValueError("max_workers must be greater than zero")
        if max_attempts <= 0:
            raise ValueError("max_attempts must be greater than zero")

        self._max_workers = max_workers
        self._max_attempts = max_attempts

    def run[T](self, task_id: str, task: Callable[[], T]) -> RetryResult[T]:
        """Run one retryable task and return its final result."""
        return self.run_all({task_id: task})[task_id]

    def run_all[T](
        self,
        tasks: Mapping[str, Callable[[], T]],
    ) -> dict[str, RetryResult[T]]:
        """Run retryable tasks concurrently and return results by task ID."""
        self._validate_tasks(tasks)

        results: dict[str, RetryResult[T]] = {}
        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            futures = [
                executor.submit(self._run_with_retries, task_id, task)
                for task_id, task in tasks.items()
            ]
            for future in as_completed(futures):
                result = future.result()
                results[result.task_id] = result

        return results

    def _validate_tasks[T](self, tasks: Mapping[str, Callable[[], T]]) -> None:
        if not tasks:
            raise ValueError("tasks must not be empty")
        if any(not task_id for task_id in tasks):
            raise ValueError("task IDs must not be empty")

    def _run_with_retries[T](
        self,
        task_id: str,
        task: Callable[[], T],
    ) -> RetryResult[T]:
        last_error: Exception | None = None
        for attempt in range(1, self._max_attempts + 1):
            try:
                return RetryResult(task_id=task_id, attempts=attempt, value=task())
            except Exception as error:
                last_error = error

        return RetryResult(
            task_id=task_id,
            attempts=self._max_attempts,
            error=last_error,
        )
