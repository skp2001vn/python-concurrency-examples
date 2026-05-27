"""Process submitted jobs with async background workers.

The business logic is an async job processing workflow: request handlers submit
jobs quickly, and a fixed number of background workers process those jobs
without blocking the request path.

The example uses `asyncio.Queue` because producers and async workers need a
safe handoff point. Workers drain submitted jobs, record handler failures, and
shutdown waits for queued work to finish before stopping worker tasks.
"""

import asyncio
from collections.abc import Awaitable, Callable


class AsyncJobQueue[T]:
    """AsyncJobQueue processes submitted jobs with async worker tasks.

    The queue is safe for use by many async producers in the same event loop.
    Callers start workers, submit jobs, wait for queued work to drain, and stop
    workers after pending jobs finish.
    """

    def __init__(
        self,
        worker_count: int,
        handler: Callable[[T], Awaitable[None]],
    ) -> None:
        """Create a queue with worker_count background job handlers."""
        if worker_count <= 0:
            raise ValueError("worker_count must be greater than zero")

        self._worker_count = worker_count
        self._handler = handler
        self._queue: asyncio.Queue[T | object] = asyncio.Queue()
        self._stop_token = object()
        self._workers: list[asyncio.Task[None]] = []
        self._started = False
        self._stopping = False
        self._failures: list[Exception] = []

    async def start(self) -> None:
        """Start the async worker tasks."""
        if self._started:
            raise RuntimeError("job queue has already been started")

        self._started = True
        self._workers = [
            asyncio.create_task(self._worker(), name=f"AsyncJobQueue-{index}")
            for index in range(self._worker_count)
        ]

    async def submit(self, job: T) -> None:
        """Submit one job for background processing."""
        if not self._started:
            raise RuntimeError("job queue has not been started")
        if self._stopping:
            raise RuntimeError("job queue is stopping")

        await self._queue.put(job)

    async def join(self) -> None:
        """Wait until all submitted jobs have finished processing."""
        await self._queue.join()

    async def stop(self) -> None:
        """Drain submitted jobs and stop all worker tasks."""
        if not self._started or self._stopping:
            return

        self._stopping = True
        await self.join()
        for _ in self._workers:
            await self._queue.put(self._stop_token)
        await asyncio.gather(*self._workers)

    def failures(self) -> tuple[Exception, ...]:
        """Return job handler exceptions captured by worker tasks."""
        return tuple(self._failures)

    async def _worker(self) -> None:
        while True:
            job = await self._queue.get()
            try:
                if job is self._stop_token:
                    return
                await self._handler(job)
            except Exception as error:
                self._failures.append(error)
            finally:
                self._queue.task_done()
