"""Reuse limited service connections across request threads.

Use `queue.Queue` to lease available connections and return them safely after
each request finishes or fails.
"""

from python_concurrency_examples.examples.connectionpool.pool import ConnectionPool

__all__ = ["ConnectionPool"]
