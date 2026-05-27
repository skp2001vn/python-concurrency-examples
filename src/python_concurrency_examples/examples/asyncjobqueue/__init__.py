"""Process submitted jobs with async background workers.

Use `asyncio.Queue` to hand off jobs from request handlers to worker tasks and
drain queued work before shutdown.
"""

from python_concurrency_examples.examples.asyncjobqueue.queue import AsyncJobQueue

__all__ = ["AsyncJobQueue"]
