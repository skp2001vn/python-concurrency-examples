"""Pass work from producers to consumers.

Use `queue.Queue` for thread-safe handoff, backpressure, and shutdown.
"""

from concurrencyexamples.boundedqueue.workqueue import BoundedQueue

__all__ = ["BoundedQueue"]
