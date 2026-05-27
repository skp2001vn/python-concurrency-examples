"""Fail fast after repeated partner API failures.

The business logic is a partner API resilience workflow: after several
consecutive failures, the service should stop calling the partner for a cooldown
period and fail fast instead.

The example uses `threading.Lock` because request threads share circuit state.
The lock protects transitions between closed, open, and half-open while partner
calls themselves run outside the lock.
"""

from collections.abc import Callable
from enum import StrEnum
from threading import Lock
from time import monotonic


class CircuitState(StrEnum):
    """CircuitState names the current partner API call policy."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(RuntimeError):
    """Raised when a partner call is rejected because the circuit is open."""


class CircuitBreaker:
    """CircuitBreaker protects calls to a flaky partner API.

    The breaker is safe for concurrent use by many threads. Calls run normally
    while closed, repeated failures open the circuit, and after the recovery
    timeout one trial call is allowed in half-open state.
    """

    def __init__(
        self,
        failure_threshold: int,
        recovery_timeout: float,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        """Create a circuit breaker with failure and cooldown limits."""
        if failure_threshold <= 0:
            raise ValueError("failure_threshold must be greater than zero")
        if recovery_timeout < 0:
            raise ValueError("recovery_timeout must not be negative")

        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._clock = clock
        self._lock = Lock()
        self._state = CircuitState.CLOSED
        self._consecutive_failures = 0
        self._opened_at: float | None = None

    def call[T](self, operation: Callable[[], T]) -> T:
        """Call the partner operation or fail fast when the circuit is open."""
        admitted_state = self._before_call()
        try:
            result = operation()
        except Exception:
            self._record_failure(admitted_state)
            raise

        self._record_success(admitted_state)
        return result

    def state(self) -> CircuitState:
        """Return the current circuit state."""
        with self._lock:
            return self._state

    def consecutive_failures(self) -> int:
        """Return the current consecutive partner failure count."""
        with self._lock:
            return self._consecutive_failures

    def _before_call(self) -> CircuitState:
        with self._lock:
            if self._state is CircuitState.CLOSED:
                return CircuitState.CLOSED
            if self._state is CircuitState.HALF_OPEN:
                raise CircuitOpenError("circuit is testing a trial call")

            if self._state is not CircuitState.OPEN or self._opened_at is None:
                raise RuntimeError("invalid circuit breaker state")
            if self._clock() - self._opened_at < self._recovery_timeout:
                raise CircuitOpenError("circuit is open")

            self._state = CircuitState.HALF_OPEN
            return CircuitState.HALF_OPEN

    def _record_success(self, admitted_state: CircuitState) -> None:
        with self._lock:
            if (
                admitted_state is CircuitState.CLOSED
                and self._state is not CircuitState.CLOSED
            ):
                return

            self._state = CircuitState.CLOSED
            self._consecutive_failures = 0
            self._opened_at = None

    def _record_failure(self, admitted_state: CircuitState) -> None:
        with self._lock:
            if admitted_state is CircuitState.HALF_OPEN:
                self._open()
                return
            if self._state is not CircuitState.CLOSED:
                return

            self._consecutive_failures += 1
            if self._consecutive_failures >= self._failure_threshold:
                self._open()

    def _open(self) -> None:
        self._state = CircuitState.OPEN
        self._opened_at = self._clock()
