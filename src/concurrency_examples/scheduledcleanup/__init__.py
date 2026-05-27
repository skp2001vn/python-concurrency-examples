"""Run periodic cleanup work in a background thread.

Use `threading.Thread` and `threading.Event` to run cleanup repeatedly and stop
the worker cooperatively.
"""

from concurrency_examples.scheduledcleanup.cleanup import (
    ScheduledCleanup,
)

__all__ = ["ScheduledCleanup"]
