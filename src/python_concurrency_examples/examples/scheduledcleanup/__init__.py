"""Run periodic cleanup work in a background thread.

Use `threading.Thread` and `threading.Event` to run cleanup repeatedly and stop
the worker cooperatively.
"""

from python_concurrency_examples.examples.scheduledcleanup.cleanup import (
    ScheduledCleanup,
)

__all__ = ["ScheduledCleanup"]
