"""Unit tests for the circuitbreaker example.

The example models a service calling a flaky partner API. The tests verify
caller-facing behavior: invalid settings are rejected, repeated failures open
the circuit, open circuits fail fast, cooldown allows one trial call, and
success or failure of that trial updates circuit state.
"""

import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event

from concurrencyexamples.circuitbreaker import (
    CircuitBreaker,
    CircuitOpenError,
    CircuitState,
)


class ManualClock:
    """ManualClock gives circuit breaker tests deterministic time."""

    def __init__(self) -> None:
        self._now = 0.0

    def __call__(self) -> float:
        return self._now

    def advance(self, seconds: float) -> None:
        """Move test time forward by seconds."""
        self._now += seconds


class CircuitBreakerTest(unittest.TestCase):
    """CircuitBreakerTest verifies the public breaker behavior."""

    # Verifies that callers must configure usable failure and cooldown limits.
    def test_rejects_invalid_settings(self) -> None:
        with self.assertRaises(ValueError):
            CircuitBreaker(failure_threshold=0, recovery_timeout=1)
        with self.assertRaises(ValueError):
            CircuitBreaker(failure_threshold=1, recovery_timeout=-1)

    # Verifies that a new breaker starts closed and allows successful calls.
    def test_starts_closed_and_records_success(self) -> None:
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=1)

        result = breaker.call(lambda: "accepted")

        self.assertEqual(result, "accepted")
        self.assertEqual(breaker.state(), CircuitState.CLOSED)
        self.assertEqual(breaker.consecutive_failures(), 0)

    # Verifies that repeated partner failures open the circuit.
    def test_opens_after_consecutive_failures(self) -> None:
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=1)

        with self.assertRaises(RuntimeError):
            breaker.call(self.raise_partner_error)
        with self.assertRaises(RuntimeError):
            breaker.call(self.raise_partner_error)

        self.assertEqual(breaker.state(), CircuitState.OPEN)
        self.assertEqual(breaker.consecutive_failures(), 2)

    # Verifies that open circuits reject calls before cooldown expires.
    def test_fails_fast_while_open(self) -> None:
        clock = ManualClock()
        breaker = CircuitBreaker(
            failure_threshold=1,
            recovery_timeout=10,
            clock=clock,
        )
        with self.assertRaises(RuntimeError):
            breaker.call(self.raise_partner_error)

        with self.assertRaises(CircuitOpenError):
            breaker.call(lambda: "should not run")

    # Verifies that a successful trial after cooldown closes the circuit.
    def test_successful_trial_after_cooldown_closes_circuit(self) -> None:
        clock = ManualClock()
        breaker = CircuitBreaker(
            failure_threshold=1,
            recovery_timeout=5,
            clock=clock,
        )
        with self.assertRaises(RuntimeError):
            breaker.call(self.raise_partner_error)
        clock.advance(5)

        result = breaker.call(lambda: "recovered")

        self.assertEqual(result, "recovered")
        self.assertEqual(breaker.state(), CircuitState.CLOSED)
        self.assertEqual(breaker.consecutive_failures(), 0)

    # Verifies that a failed trial after cooldown reopens the circuit.
    def test_failed_trial_after_cooldown_reopens_circuit(self) -> None:
        clock = ManualClock()
        breaker = CircuitBreaker(
            failure_threshold=1,
            recovery_timeout=5,
            clock=clock,
        )
        with self.assertRaises(RuntimeError):
            breaker.call(self.raise_partner_error)
        clock.advance(5)

        with self.assertRaises(RuntimeError):
            breaker.call(self.raise_partner_error)

        self.assertEqual(breaker.state(), CircuitState.OPEN)
        with self.assertRaises(CircuitOpenError):
            breaker.call(lambda: "blocked")

    # Verifies that a success after a single failure resets the failure counter.
    def test_success_resets_failure_count_before_threshold(self) -> None:
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=1)

        with self.assertRaises(RuntimeError):
            breaker.call(self.raise_partner_error)
        breaker.call(lambda: "accepted")

        self.assertEqual(breaker.state(), CircuitState.CLOSED)
        self.assertEqual(breaker.consecutive_failures(), 0)

    # Verifies that an older successful call does not close a newly opened circuit.
    def test_in_flight_success_does_not_close_opened_circuit(self) -> None:
        breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=10)
        both_calls_started = Barrier(3)
        release_success = Event()

        def slow_success() -> str:
            both_calls_started.wait(timeout=1)
            if not release_success.wait(timeout=1):
                raise AssertionError("timed out waiting to release success")
            return "accepted"

        def fail_fast() -> None:
            both_calls_started.wait(timeout=1)
            raise RuntimeError("partner failed")

        with ThreadPoolExecutor(max_workers=2) as executor:
            success = executor.submit(breaker.call, slow_success)
            failure = executor.submit(breaker.call, fail_fast)
            try:
                both_calls_started.wait(timeout=1)

                with self.assertRaises(RuntimeError):
                    failure.result(timeout=1)
                self.assertEqual(breaker.state(), CircuitState.OPEN)
            finally:
                release_success.set()

            self.assertEqual(success.result(timeout=1), "accepted")

        self.assertEqual(breaker.state(), CircuitState.OPEN)

    # Verifies that only one half-open trial call is allowed after cooldown.
    def test_half_open_allows_one_trial_call(self) -> None:
        clock = ManualClock()
        breaker = CircuitBreaker(
            failure_threshold=1,
            recovery_timeout=5,
            clock=clock,
        )
        with self.assertRaises(RuntimeError):
            breaker.call(self.raise_partner_error)
        clock.advance(5)
        trial_started = Event()
        release_trial = Event()

        def trial_call() -> str:
            trial_started.set()
            if not release_trial.wait(timeout=1):
                raise AssertionError("timed out waiting to release trial")
            return "recovered"

        with ThreadPoolExecutor(max_workers=1) as executor:
            trial = executor.submit(breaker.call, trial_call)
            try:
                self.assertTrue(trial_started.wait(timeout=1))
                self.assertEqual(breaker.state(), CircuitState.HALF_OPEN)

                with self.assertRaises(CircuitOpenError):
                    breaker.call(lambda: "blocked")
            finally:
                release_trial.set()

            self.assertEqual(trial.result(timeout=1), "recovered")

        self.assertEqual(breaker.state(), CircuitState.CLOSED)

    def raise_partner_error(self) -> None:
        """Raise a fixed error from a simulated partner API call."""
        raise RuntimeError("partner failed")


if __name__ == "__main__":
    unittest.main()
