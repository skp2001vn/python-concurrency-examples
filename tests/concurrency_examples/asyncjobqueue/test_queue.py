"""Unit tests for the asyncjobqueue example.

The example models async request handlers submitting jobs to background worker
tasks. The tests verify caller-facing behavior: invalid worker counts are
rejected, submissions require a running queue, queued jobs are processed,
workers run concurrently, failures are captured, and shutdown drains pending
work before rejecting new submissions.
"""

import asyncio
import unittest

from concurrency_examples.asyncjobqueue import AsyncJobQueue


class AsyncJobQueueTest(unittest.IsolatedAsyncioTestCase):
    """AsyncJobQueueTest verifies the public async worker behavior."""

    # Verifies that callers must choose a positive worker count.
    async def test_rejects_invalid_worker_count(self) -> None:
        with self.assertRaises(ValueError):
            AsyncJobQueue(worker_count=0, handler=self.handle_job)

    # Verifies that jobs cannot be submitted before workers start.
    async def test_rejects_submit_before_start(self) -> None:
        queue = AsyncJobQueue(worker_count=1, handler=self.handle_job)

        with self.assertRaises(RuntimeError):
            await queue.submit("job-1")

    # Verifies that the worker group can only be started once.
    async def test_rejects_double_start(self) -> None:
        queue = AsyncJobQueue(worker_count=1, handler=self.handle_job)
        await queue.start()
        self.addAsyncCleanup(queue.stop)

        with self.assertRaises(RuntimeError):
            await queue.start()

    # Verifies that submitted jobs are processed by workers.
    async def test_processes_submitted_jobs(self) -> None:
        processed: list[str] = []

        async def handler(job: str) -> None:
            processed.append(job)

        queue = AsyncJobQueue(worker_count=1, handler=handler)
        await queue.start()
        self.addAsyncCleanup(queue.stop)

        await queue.submit("job-1")
        await queue.submit("job-2")
        await queue.join()

        self.assertEqual(processed, ["job-1", "job-2"])

    # Verifies that multiple async workers process jobs concurrently.
    async def test_processes_jobs_concurrently(self) -> None:
        worker_count = 3
        active_count = 0
        peak_active_count = 0
        active_lock = asyncio.Lock()
        all_started = asyncio.Event()
        release_jobs = asyncio.Event()

        async def handler(job: str) -> None:
            nonlocal active_count, peak_active_count
            async with active_lock:
                active_count += 1
                peak_active_count = max(peak_active_count, active_count)
                if active_count == worker_count:
                    all_started.set()

            try:
                await release_jobs.wait()
            finally:
                async with active_lock:
                    active_count -= 1

        queue = AsyncJobQueue(worker_count=worker_count, handler=handler)
        await queue.start()

        async def cleanup_queue() -> None:
            release_jobs.set()
            await queue.stop()

        self.addAsyncCleanup(cleanup_queue)

        for index in range(worker_count):
            await queue.submit(f"job-{index}")

        await asyncio.wait_for(all_started.wait(), timeout=1)
        self.assertEqual(peak_active_count, worker_count)

        release_jobs.set()
        await asyncio.wait_for(queue.join(), timeout=1)

    # Verifies that handler failures are captured and queue accounting completes.
    async def test_captures_handler_failures(self) -> None:
        async def handler(job: str) -> None:
            raise RuntimeError(f"{job} failed")

        queue = AsyncJobQueue(worker_count=1, handler=handler)
        await queue.start()
        self.addAsyncCleanup(queue.stop)

        await queue.submit("job-1")
        await queue.join()

        failures = queue.failures()
        self.assertEqual(len(failures), 1)
        self.assertIsInstance(failures[0], RuntimeError)

    # Verifies that stop drains queued work and rejects later submissions.
    async def test_stop_drains_pending_jobs_and_rejects_later_submissions(self) -> None:
        processed: list[str] = []

        async def handler(job: str) -> None:
            processed.append(job)

        queue = AsyncJobQueue(worker_count=1, handler=handler)
        await queue.start()

        await queue.submit("job-1")
        await queue.submit("job-2")
        await queue.stop()

        self.assertEqual(processed, ["job-1", "job-2"])
        with self.assertRaises(RuntimeError):
            await queue.submit("job-3")

    async def handle_job(self, job: str) -> None:
        """Handle one test job successfully."""
        return None


if __name__ == "__main__":
    unittest.main()
