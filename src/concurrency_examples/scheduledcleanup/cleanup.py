"""Run periodic cleanup work in a background thread.

The business logic is a maintenance workflow: a service periodically removes
expired sessions, temporary files, or stale records without making request
handlers do that cleanup work.

The example uses `threading.Thread` for the background worker and
`threading.Event` for cooperative shutdown. The stop signal wakes the worker
promptly so callers can shut the service down cleanly.
"""

from collections.abc import Callable
from threading import Event, Lock, Thread


class ScheduledCleanup:
    """ScheduledCleanup runs maintenance work until stopped.

    The cleanup worker starts at most once and runs in one background thread.
    Callers can stop it cooperatively, inspect captured cleanup errors, and
    check whether the worker is still running.
    """

    def __init__(self, cleanup: Callable[[], None], interval: float) -> None:
        """Create a cleanup worker that runs after each interval."""
        if interval <= 0:
            raise ValueError("interval must be greater than zero")

        self._cleanup = cleanup
        self._interval = interval
        self._stop_requested = Event()
        self._lock = Lock()
        self._thread: Thread | None = None
        self._started = False
        self._errors: list[Exception] = []

    def start(self) -> None:
        """Start the background cleanup worker."""
        with self._lock:
            if self._started:
                raise RuntimeError("cleanup worker has already been started")

            self._started = True
            self._stop_requested.clear()
            self._thread = Thread(
                target=self._run,
                name="ScheduledCleanup",
                daemon=True,
            )
            self._thread.start()

    def stop(self, timeout: float | None = None) -> bool:
        """Request shutdown and return whether the worker stopped in time."""
        with self._lock:
            thread = self._thread

        if thread is None:
            return True

        self._stop_requested.set()
        thread.join(timeout=timeout)
        return not thread.is_alive()

    def is_running(self) -> bool:
        """Return whether the cleanup worker thread is currently running."""
        with self._lock:
            thread = self._thread
        return thread is not None and thread.is_alive()

    def errors(self) -> tuple[Exception, ...]:
        """Return cleanup exceptions captured from the worker thread."""
        with self._lock:
            return tuple(self._errors)

    def _run(self) -> None:
        while not self._stop_requested.wait(self._interval):
            try:
                self._cleanup()
            except Exception as error:
                with self._lock:
                    self._errors.append(error)
