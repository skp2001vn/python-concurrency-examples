"""Limit partner file downloads during a reporting job.

Use `threading.Semaphore` to cap active download workers and release capacity
when each download finishes or fails.
"""

from python_concurrency_examples.examples.downloadpool.pool import DownloadPool

__all__ = ["DownloadPool"]
