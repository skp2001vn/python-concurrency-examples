"""Reuse limited service connections across request threads.

The business logic is a connection leasing workflow: a service has a small set
of reusable database or API connections, and many request handlers need to
borrow one before they can do work.

The example uses `queue.Queue` because it already provides thread-safe blocking
handoff for reusable resources. A checkout removes one connection from the
pool, and the context manager returns it even if the request handler fails.
"""

from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from queue import Queue


class ConnectionPool[T]:
    """ConnectionPool leases a fixed set of reusable connections.

    The pool is safe for concurrent use by many threads. Callers check out one
    connection at a time, optionally time out while waiting for availability,
    and automatically return the connection when the context exits.
    """

    def __init__(self, connections: Iterable[T]) -> None:
        """Create a pool from the provided reusable connections."""
        connection_list = list(connections)
        if not connection_list:
            raise ValueError("connections must not be empty")

        self._available: Queue[T] = Queue(maxsize=len(connection_list))
        for connection in connection_list:
            self._available.put_nowait(connection)

    @contextmanager
    def checkout(self, timeout: float | None = None) -> Iterator[T]:
        """Lease one connection until the context exits."""
        connection = self._available.get(timeout=timeout)
        try:
            yield connection
        finally:
            self._available.put_nowait(connection)

    def available_count(self) -> int:
        """Return the approximate number of currently available connections."""
        return self._available.qsize()
