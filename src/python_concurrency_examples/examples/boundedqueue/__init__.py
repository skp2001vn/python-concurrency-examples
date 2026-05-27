"""Pass work from producers to consumers.

Use `queue.Queue` for thread-safe handoff, blocking, and backpressure.
"""

from python_concurrency_examples.examples.boundedqueue.workqueue import BoundedQueue

__all__ = ["BoundedQueue"]
