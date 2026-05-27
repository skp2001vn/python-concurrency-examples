"""Upload many files with limited async concurrency.

The business logic is a batch upload workflow: a service needs to upload many
files to object storage, but only a few uploads should run at the same time to
avoid overwhelming storage or network capacity.

The example uses `asyncio.Semaphore` because all uploads can be scheduled as
async tasks while the semaphore caps how many are actively uploading. Each file
returns a result so callers can see which uploads succeeded or failed.
"""

import asyncio
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class UploadResult[T]:
    """UploadResult reports the final outcome for one file upload.

    Attributes:
        file_name: Business identifier for the uploaded file.
        value: Successful upload result, or None when upload failed.
        error: Final exception, or None when upload succeeded.
    """

    file_name: str
    value: T | None = None
    error: Exception | None = None

    @property
    def succeeded(self) -> bool:
        """Return whether the upload completed successfully."""
        return self.error is None


class AsyncBatchUploader:
    """AsyncBatchUploader uploads files with bounded async concurrency.

    The uploader schedules independent file uploads concurrently. A semaphore
    limits active uploads, and callers receive one structured result per file
    instead of losing the whole batch to one upload failure.
    """

    def __init__(self, max_concurrent: int) -> None:
        """Create an uploader that runs at most max_concurrent uploads."""
        if max_concurrent <= 0:
            raise ValueError("max_concurrent must be greater than zero")

        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def upload_all[T](
        self,
        uploads: Mapping[str, Callable[[], Awaitable[T]]],
    ) -> dict[str, UploadResult[T]]:
        """Upload all files and return results by file name."""
        self._validate_uploads(uploads)

        tasks = [
            asyncio.create_task(self._upload_one(file_name, upload))
            for file_name, upload in uploads.items()
        ]
        results = await asyncio.gather(*tasks)
        return {
            result.file_name: result
            for result in results
        }

    def _validate_uploads[T](
        self,
        uploads: Mapping[str, Callable[[], Awaitable[T]]],
    ) -> None:
        if not uploads:
            raise ValueError("uploads must not be empty")
        if any(not file_name for file_name in uploads):
            raise ValueError("file names must not be empty")

    async def _upload_one[T](
        self,
        file_name: str,
        upload: Callable[[], Awaitable[T]],
    ) -> UploadResult[T]:
        async with self._semaphore:
            try:
                return UploadResult(file_name=file_name, value=await upload())
            except Exception as error:
                return UploadResult(file_name=file_name, error=error)
