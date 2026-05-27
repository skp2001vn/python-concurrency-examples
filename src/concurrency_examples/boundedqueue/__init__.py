"""Pass work from producers to consumers.

Use `queue.Queue` for thread-safe handoff, backpressure, and shutdown.
"""

from concurrency_examples.boundedqueue.workqueue import BoundedQueue

__all__ = ["BoundedQueue"]
