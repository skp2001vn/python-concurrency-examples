"""Fail fast after repeated partner API failures.

Use `threading.Lock` to protect circuit state transitions across request
threads.
"""

from concurrencyexamples.circuitbreaker.breaker import (
    CircuitBreaker,
    CircuitOpenError,
    CircuitState,
)

__all__ = ["CircuitBreaker", "CircuitOpenError", "CircuitState"]
