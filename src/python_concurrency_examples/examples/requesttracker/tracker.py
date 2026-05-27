"""Drain in-flight requests during graceful service shutdown.

The business logic is a service shutdown workflow: once shutdown begins, new
requests should be rejected while existing request handlers are allowed to
finish before the process exits.

The example uses `threading.Condition` because shutdown waits for a shared
active-request count to reach zero. Each request increments the count when it
starts, decrements it when it finishes, and wakes shutdown waiters when the
service is drained.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from threading import Condition


class ShutdownStartedError(RuntimeError):
    """Raised when a caller tries to start work after shutdown begins."""


class RequestTracker:
    """RequestTracker coordinates request admission and graceful shutdown.

    The tracker is safe for concurrent use by many threads. Request handlers use
    `track_request()` as a context manager so active counts are cleaned up on
    success or failure, while shutdown code stops new work and waits for active
    requests to drain.
    """

    def __init__(self) -> None:
        """Create a tracker that accepts requests and has no active work."""
        self._condition = Condition()
        self._active_requests = 0
        self._shutdown_started = False

    @contextmanager
    def track_request(self) -> Iterator[None]:
        """Track one active request until its handler exits."""
        with self._condition:
            if self._shutdown_started:
                raise ShutdownStartedError("shutdown has already started")
            self._active_requests += 1

        try:
            yield
        finally:
            with self._condition:
                self._active_requests -= 1
                if self._active_requests == 0:
                    self._condition.notify_all()

    def begin_shutdown(self) -> None:
        """Stop accepting new requests and wake waiters if already drained."""
        with self._condition:
            self._shutdown_started = True
            if self._active_requests == 0:
                self._condition.notify_all()

    def wait_until_drained(self, timeout: float | None = None) -> bool:
        """Block until all active requests finish or timeout expires."""
        with self._condition:
            return self._condition.wait_for(self._is_drained, timeout=timeout)

    def active_requests(self) -> int:
        """Return the current number of active request handlers."""
        with self._condition:
            return self._active_requests

    def is_shutting_down(self) -> bool:
        """Return whether graceful shutdown has started."""
        with self._condition:
            return self._shutdown_started

    def _is_drained(self) -> bool:
        return self._active_requests == 0
