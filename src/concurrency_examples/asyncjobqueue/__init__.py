"""Process submitted jobs with async background workers.

Use `asyncio.Queue` to hand off jobs from request handlers to worker tasks and
drain queued work before shutdown.
"""

from concurrency_examples.asyncjobqueue.queue import AsyncJobQueue

__all__ = ["AsyncJobQueue"]
