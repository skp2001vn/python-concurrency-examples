"""Limit simultaneous third-party API calls.

The business logic is a third-party API workflow: a service can send many
requests, but only a fixed number should be in flight at once to respect a
partner quota or protect the remote service.

The example uses `threading.BoundedSemaphore` because each API call needs one
permit and every acquired permit must be released exactly once. The context
manager keeps permit ownership explicit even when an API call fails.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from threading import BoundedSemaphore


class ApiRateLimiter:
    """ApiRateLimiter caps simultaneous third-party API calls.

    The limiter is safe for concurrent use by many threads. Callers acquire one
    permit before calling the API, optionally time out while waiting, and
    automatically release the permit when the context exits.
    """

    def __init__(self, max_in_flight: int) -> None:
        """Create a limiter for at most max_in_flight active API calls."""
        if max_in_flight <= 0:
            raise ValueError("max_in_flight must be greater than zero")

        self._permits = BoundedSemaphore(max_in_flight)

    @contextmanager
    def acquire(self, timeout: float | None = None) -> Iterator[None]:
        """Lease one API call permit until the context exits."""
        acquired = self._acquire_permit(timeout)
        if not acquired:
            raise TimeoutError("timed out waiting for API call permit")

        try:
            yield
        finally:
            self._permits.release()

    def _acquire_permit(self, timeout: float | None) -> bool:
        if timeout is None:
            return self._permits.acquire()
        return self._permits.acquire(timeout=timeout)
