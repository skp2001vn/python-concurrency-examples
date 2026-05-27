"""Unit tests for the asyncbatchuploader example.

The example models uploading many files to object storage with bounded async
concurrency. The tests verify caller-facing behavior: invalid batches are
rejected, successful uploads return results, failures are captured per file, and
active uploads never exceed the configured concurrency limit.
"""

import asyncio
import unittest

from concurrencyexamples.asyncbatchuploader import (
    AsyncBatchUploader,
    UploadResult,
)


class AsyncBatchUploaderTest(unittest.IsolatedAsyncioTestCase):
    """AsyncBatchUploaderTest verifies the public batch upload behavior."""

    # Verifies that callers must choose a positive upload limit.
    async def test_rejects_invalid_concurrency_limit(self) -> None:
        with self.assertRaises(ValueError):
            AsyncBatchUploader(max_concurrent=0)

    # Verifies that callers must provide at least one named upload.
    async def test_rejects_invalid_upload_batch(self) -> None:
        uploader = AsyncBatchUploader(max_concurrent=1)

        with self.assertRaises(ValueError):
            await uploader.upload_all({})
        with self.assertRaises(ValueError):
            await uploader.upload_all({"": self.upload_invoice})

    # Verifies that successful uploads return one result per file.
    async def test_returns_successful_upload_results(self) -> None:
        uploader = AsyncBatchUploader(max_concurrent=2)

        results = await uploader.upload_all(
            {
                "invoice-1.pdf": lambda: self.upload_value("stored-1"),
                "invoice-2.pdf": lambda: self.upload_value("stored-2"),
            },
        )

        self.assertEqual(
            results,
            {
                "invoice-1.pdf": UploadResult(
                    file_name="invoice-1.pdf",
                    value="stored-1",
                ),
                "invoice-2.pdf": UploadResult(
                    file_name="invoice-2.pdf",
                    value="stored-2",
                ),
            },
        )

    # Verifies that one failed file does not hide other file results.
    async def test_captures_upload_failures_per_file(self) -> None:
        uploader = AsyncBatchUploader(max_concurrent=2)

        results = await uploader.upload_all(
            {
                "invoice-1.pdf": lambda: self.upload_value("stored-1"),
                "invoice-2.pdf": self.fail_upload,
            },
        )

        self.assertTrue(results["invoice-1.pdf"].succeeded)
        self.assertEqual(results["invoice-1.pdf"].value, "stored-1")
        self.assertFalse(results["invoice-2.pdf"].succeeded)
        self.assertIsInstance(results["invoice-2.pdf"].error, RuntimeError)

    # Verifies that the semaphore caps active async upload tasks.
    async def test_limits_active_uploads(self) -> None:
        max_concurrent = 3
        upload_count = 10
        uploader = AsyncBatchUploader(max_concurrent=max_concurrent)
        active_count = 0
        peak_active_count = 0
        active_lock = asyncio.Lock()
        first_wave_ready = asyncio.Event()
        release_uploads = asyncio.Event()

        async def upload_file(name: str) -> str:
            nonlocal active_count, peak_active_count
            async with active_lock:
                active_count += 1
                peak_active_count = max(peak_active_count, active_count)
                if active_count > max_concurrent:
                    raise AssertionError("too many active uploads")
                if active_count == max_concurrent:
                    first_wave_ready.set()

            try:
                await release_uploads.wait()
                return f"{name}:stored"
            finally:
                async with active_lock:
                    active_count -= 1

        uploads = {
            f"invoice-{index}.pdf": lambda index=index: upload_file(
                f"invoice-{index}.pdf",
            )
            for index in range(upload_count)
        }
        upload_task = asyncio.create_task(uploader.upload_all(uploads))
        try:
            await asyncio.wait_for(first_wave_ready.wait(), timeout=1)
            self.assertEqual(peak_active_count, max_concurrent)

            release_uploads.set()
            results = await asyncio.wait_for(upload_task, timeout=1)
        finally:
            release_uploads.set()
            if not upload_task.done():
                await asyncio.wait_for(upload_task, timeout=1)

        self.assertEqual(peak_active_count, max_concurrent)
        self.assertTrue(all(result.succeeded for result in results.values()))

    async def upload_invoice(self) -> str:
        """Return a fixed upload result."""
        return "stored"

    async def upload_value(self, value: str) -> str:
        """Return the provided upload result."""
        return value

    async def fail_upload(self) -> str:
        """Raise a fixed upload error."""
        raise RuntimeError("upload failed")


if __name__ == "__main__":
    unittest.main()
