"""Wait for startup work before accepting service requests.

The business logic is a service startup workflow: request handlers should not
accept traffic until configuration is loaded, database connections are open, or
a cache is warm.

The example uses `threading.Event` because readiness is a one-time signal that
many waiting threads can observe. Once startup is marked ready, current and
future waiters can continue without additional coordination.
"""

from threading import Event


class ServiceStartup:
    """ServiceStartup coordinates a one-way service readiness signal.

    The startup state is safe for concurrent use by many threads. Request
    handlers can wait for readiness with an optional timeout, and startup code
    can mark the service ready exactly once in an idempotent way.
    """

    def __init__(self) -> None:
        """Create a startup signal that begins in the not-ready state."""
        self._ready = Event()

    def mark_ready(self) -> None:
        """Mark startup complete and release all current and future waiters."""
        self._ready.set()

    def wait_until_ready(self, timeout: float | None = None) -> bool:
        """Block until startup is ready or timeout expires."""
        return self._ready.wait(timeout=timeout)

    def is_ready(self) -> bool:
        """Return whether startup has been marked ready."""
        return self._ready.is_set()
