"""Drain in-flight requests during graceful service shutdown.

Use `threading.Condition` to reject new requests after shutdown starts and wake
callers waiting for active requests to finish.
"""

from python_concurrency_examples.examples.requesttracker.tracker import (
    RequestTracker,
    ShutdownStartedError,
)

__all__ = ["RequestTracker", "ShutdownStartedError"]
