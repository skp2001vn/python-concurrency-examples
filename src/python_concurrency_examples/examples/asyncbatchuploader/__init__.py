"""Upload many files with limited async concurrency.

Use `asyncio.Semaphore` to cap active upload tasks while still returning one
result for every file in the batch.
"""

from python_concurrency_examples.examples.asyncbatchuploader.uploader import (
    AsyncBatchUploader,
    UploadResult,
)

__all__ = ["AsyncBatchUploader", "UploadResult"]
