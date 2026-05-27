"""Limit partner file downloads during a reporting job.

The business logic is a reporting workflow: many files need to be fetched from
partner systems, but only a few downloads should run at the same time to avoid
overwhelming the network or partner API.

The example uses `threading.Semaphore` because a fixed number of download slots
can be shared safely across many worker threads. Each caller acquires one slot,
runs its download, and releases the slot even if the download fails.
"""

from collections.abc import Callable
from threading import Semaphore


class DownloadPool:
    """DownloadPool limits how many download tasks run at once.

    The pool is safe for concurrent use by many threads. Callers submit one
    download task at a time, optionally time out while waiting for capacity, and
    receive the task result or original exception.
    """

    def __init__(self, max_concurrent: int) -> None:
        """Create a pool with at most max_concurrent active downloads."""
        if max_concurrent <= 0:
            raise ValueError("max_concurrent must be greater than zero")

        self._slots = Semaphore(max_concurrent)

    def run[T](
        self,
        download_id: str,
        download: Callable[[], T],
        timeout: float | None = None,
    ) -> T:
        """Run one download when capacity is available and return its result."""
        if not download_id:
            raise ValueError("download_id must not be empty")

        acquired = self._acquire_slot(timeout)
        if not acquired:
            raise TimeoutError(f"timed out waiting for download slot: {download_id!r}")

        try:
            return download()
        finally:
            self._slots.release()

    def _acquire_slot(self, timeout: float | None) -> bool:
        if timeout is None:
            return self._slots.acquire()
        return self._slots.acquire(timeout=timeout)
