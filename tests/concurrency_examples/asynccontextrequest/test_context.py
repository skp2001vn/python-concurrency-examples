"""Unit tests for the asynccontextrequest example.

The example models request IDs used for logging, auditing, or tracing in async
request tasks. The tests verify caller-facing behavior: blank IDs are rejected,
request IDs can be set and reset, and sibling async tasks keep independent
request contexts.
"""

import asyncio
import unittest

from concurrency_examples.asynccontextrequest import (
    AsyncRequestContext,
)


class AsyncRequestContextTest(unittest.IsolatedAsyncioTestCase):
    """AsyncRequestContextTest verifies the public context variable behavior."""

    # Verifies that a new async context starts without a request ID.
    async def test_starts_without_request_id(self) -> None:
        context = AsyncRequestContext()

        self.assertIsNone(context.get_request_id())

    # Verifies that request IDs must be non-empty.
    async def test_rejects_blank_request_id(self) -> None:
        context = AsyncRequestContext()

        with self.assertRaises(ValueError):
            context.set_request_id("")

    # Verifies that one task can set, read, and reset its request ID.
    async def test_sets_and_resets_request_id(self) -> None:
        context = AsyncRequestContext()

        token = context.set_request_id("req-1")
        self.assertEqual(context.get_request_id(), "req-1")

        context.reset(token)

        self.assertIsNone(context.get_request_id())

    # Verifies that sibling async tasks do not share request IDs.
    async def test_request_ids_are_isolated_per_task(self) -> None:
        task_count = 6
        context = AsyncRequestContext()
        ready_count = 0
        ready_lock = asyncio.Lock()
        all_ready = asyncio.Event()
        release_tasks = asyncio.Event()

        async def handle_request(index: int) -> tuple[str, str | None]:
            nonlocal ready_count
            request_id = f"req-{index}"
            context.set_request_id(request_id)
            async with ready_lock:
                ready_count += 1
                if ready_count == task_count:
                    all_ready.set()

            await release_tasks.wait()
            return request_id, context.get_request_id()

        tasks = [
            asyncio.create_task(handle_request(index))
            for index in range(task_count)
        ]
        try:
            await asyncio.wait_for(all_ready.wait(), timeout=1)
            self.assertIsNone(context.get_request_id())

            release_tasks.set()
            results = await asyncio.wait_for(asyncio.gather(*tasks), timeout=1)
        finally:
            release_tasks.set()

        self.assertEqual(
            set(results),
            {(f"req-{index}", f"req-{index}") for index in range(task_count)},
        )

    # Verifies that resetting one task does not affect another task's context.
    async def test_reset_affects_only_current_task(self) -> None:
        context = AsyncRequestContext()
        worker_ready = asyncio.Event()
        worker_done = asyncio.Event()

        async def worker() -> str | None:
            context.set_request_id("worker-req")
            worker_ready.set()
            await worker_done.wait()
            return context.get_request_id()

        task = asyncio.create_task(worker())
        try:
            await asyncio.wait_for(worker_ready.wait(), timeout=1)

            token = context.set_request_id("main-req")
            context.reset(token)
            worker_done.set()

            self.assertEqual(await asyncio.wait_for(task, timeout=1), "worker-req")
        finally:
            worker_done.set()

        self.assertIsNone(context.get_request_id())


if __name__ == "__main__":
    unittest.main()
