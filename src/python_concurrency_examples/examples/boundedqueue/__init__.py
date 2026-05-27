"""Pass work from producers to consumers.

Use `queue.Queue` for thread-safe handoff, backpressure, and shutdown.
"""

from python_concurrency_examples.examples.boundedqueue.workqueue import BoundedQueue

__all__ = ["BoundedQueue"]
