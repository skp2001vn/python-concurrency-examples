"""Track request metrics from many concurrent callers.

The business logic is a small metrics collector: callers record started
requests, successful completions, failed completions, and the highest number of
requests that were in flight at the same time.

The example uses `threading.Lock` because the counters form one shared snapshot.
The lock keeps increments, decrements, and peak in-flight updates consistent for
all threads.
"""

from dataclasses import dataclass
from threading import Lock


@dataclass(frozen=True, slots=True)
class Snapshot:
    """Snapshot reports the metric values observed at one moment in time.

    Attributes:
        requests: Number of requests that have started.
        success: Number of requests that completed successfully.
        failure: Number of requests that completed with failure.
        in_flight: Number of requests currently active.
        peak_in_flight: Highest observed number of active requests.
    """

    requests: int = 0
    success: int = 0
    failure: int = 0
    in_flight: int = 0
    peak_in_flight: int = 0


class Metrics:
    """Metrics tracks request counts with lock-protected integer operations.

    Metrics is useful for high-frequency observations where each counter can be
    updated through a small critical section. It is safe for concurrent use by
    multiple threads.
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self._requests = 0
        self._success = 0
        self._failure = 0
        self._in_flight = 0
        self._peak_in_flight = 0

    def start(self) -> int:
        """Record that one request has begun and return the active count."""
        with self._lock:
            self._requests += 1
            self._in_flight += 1
            self._peak_in_flight = max(self._peak_in_flight, self._in_flight)
            return self._in_flight

    def succeed(self) -> int:
        """Record one successful request and return the remaining active count."""
        with self._lock:
            self._ensure_active_request()
            self._success += 1
            self._in_flight -= 1
            return self._in_flight

    def fail(self) -> int:
        """Record one failed request and return the remaining active count."""
        with self._lock:
            self._ensure_active_request()
            self._failure += 1
            self._in_flight -= 1
            return self._in_flight

    def snapshot(self) -> Snapshot:
        """Return the current metrics."""
        with self._lock:
            return Snapshot(
                requests=self._requests,
                success=self._success,
                failure=self._failure,
                in_flight=self._in_flight,
                peak_in_flight=self._peak_in_flight,
            )

    def reset(self) -> None:
        """Clear all counters."""
        with self._lock:
            self._requests = 0
            self._success = 0
            self._failure = 0
            self._in_flight = 0
            self._peak_in_flight = 0

    def _ensure_active_request(self) -> None:
        if self._in_flight == 0:
            raise RuntimeError("no active request to complete")
