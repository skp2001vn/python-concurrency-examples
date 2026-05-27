"""Pass work items from producers to consumers with bounded capacity.

The business logic is a small work queue: callers submit jobs while worker
threads take jobs for processing. The queue blocks producers when capacity is
full and blocks consumers when no work is available.

The example uses `queue.Queue` because it owns the internal locking and
condition signaling needed for safe handoff between many threads.
"""

from __future__ import annotations

from queue import Queue
from typing import Generic, TypeVar


T = TypeVar("T")


class BoundedQueue(Generic[T]):
    """BoundedQueue coordinates work handoff between producer and consumer threads.

    The queue is safe for concurrent use by many threads. Producers may block
    when the queue is full, and consumers may block when the queue is empty.
    """

    def __init__(self, capacity: int) -> None:
        """Create a queue that stores at most capacity pending items."""
        if capacity <= 0:
            raise ValueError("capacity must be greater than zero")
        self._queue: Queue[T] = Queue(maxsize=capacity)

    def put(self, item: T, timeout: float | None = None) -> None:
        """Add an item, blocking until space is available or timeout expires."""
        self._queue.put(item, timeout=timeout)

    def get(self, timeout: float | None = None) -> T:
        """Remove and return an item, blocking until one is available or timeout expires."""
        return self._queue.get(timeout=timeout)

    def task_done(self) -> None:
        """Mark one previously returned item as processed."""
        self._queue.task_done()

    def join(self) -> None:
        """Block until all submitted items have been marked as processed."""
        self._queue.join()

    def size(self) -> int:
        """Return the approximate number of pending items."""
        return self._queue.qsize()
