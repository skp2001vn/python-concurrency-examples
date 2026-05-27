"""Unit tests for the asyncreviewbatch example.

The example models vendor changes, policy exceptions, or compliance documents
that need several async approvals before release. The tests verify
caller-facing behavior: required reviewers are validated, approvals are
idempotent, waiters can time out, and async reviewer tasks release all waiting
callers by completing the approval set.
"""

import asyncio
import unittest

from concurrency_examples.asyncreviewbatch import AsyncReviewBatch


class AsyncReviewBatchTest(unittest.IsolatedAsyncioTestCase):
    """AsyncReviewBatchTest verifies the public async review behavior."""

    # Verifies that callers must configure at least one reviewer.
    async def test_rejects_empty_reviewer_set(self) -> None:
        with self.assertRaises(ValueError):
            AsyncReviewBatch([])

    # Verifies that blank reviewer names are not valid configuration.
    async def test_rejects_blank_reviewer_names(self) -> None:
        with self.assertRaises(ValueError):
            AsyncReviewBatch(["finance", ""])

    # Verifies that each required reviewer can approve exactly once.
    async def test_records_required_approvals(self) -> None:
        batch = AsyncReviewBatch(["finance", "legal"])

        self.assertTrue(await batch.approve("finance"))
        self.assertFalse(await batch.approve("finance"))
        self.assertFalse(await batch.is_approved())
        self.assertEqual(await batch.approved_by(), frozenset({"finance"}))
        self.assertEqual(await batch.remaining_reviewers(), frozenset({"legal"}))

        self.assertTrue(await batch.approve("legal"))

        self.assertTrue(await batch.is_approved())
        self.assertEqual(await batch.remaining_reviewers(), frozenset())

    # Verifies that callers cannot approve with a reviewer outside the batch.
    async def test_rejects_unexpected_reviewer(self) -> None:
        batch = AsyncReviewBatch(["finance"])

        with self.assertRaises(ValueError):
            await batch.approve("manager")

        self.assertEqual(await batch.approved_by(), frozenset())

    # Verifies that waiters return immediately when the batch is already approved.
    async def test_wait_returns_true_when_already_approved(self) -> None:
        batch = AsyncReviewBatch(["finance"])
        await batch.approve("finance")

        self.assertTrue(await batch.wait_until_approved(timeout=0))

    # Verifies that waiters can time out while approvals are incomplete.
    async def test_wait_returns_false_on_timeout(self) -> None:
        batch = AsyncReviewBatch(["finance", "legal"])
        await batch.approve("finance")

        self.assertFalse(await batch.wait_until_approved(timeout=0.01))

    # Verifies that negative timeout values are rejected.
    async def test_rejects_negative_timeout(self) -> None:
        batch = AsyncReviewBatch(["finance"])

        with self.assertRaises(ValueError):
            await batch.wait_until_approved(timeout=-1)

    # Verifies that one completed approval set wakes all waiting callers.
    async def test_approval_completion_wakes_all_waiters(self) -> None:
        reviewers = ["finance", "legal", "manager"]
        waiter_count = 5
        batch = AsyncReviewBatch(reviewers)
        waiters = [
            asyncio.create_task(batch.wait_until_approved(timeout=1))
            for _ in range(waiter_count)
        ]

        await asyncio.sleep(0)
        self.assertTrue(all(not waiter.done() for waiter in waiters))

        await asyncio.gather(*(batch.approve(reviewer) for reviewer in reviewers))
        results = await asyncio.wait_for(asyncio.gather(*waiters), timeout=1)

        self.assertEqual(results, [True] * waiter_count)
        self.assertEqual(await batch.approved_by(), frozenset(reviewers))

    # Verifies that async reviewer tasks release a waiter for the whole batch.
    async def test_waiter_returns_after_async_reviewers_approve(self) -> None:
        reviewers = ["finance", "legal", "manager"]
        batch = AsyncReviewBatch(reviewers)
        started_count = 0
        all_started = asyncio.Event()
        release_reviewers = asyncio.Event()
        started_lock = asyncio.Lock()

        async def approve(reviewer: str) -> bool:
            nonlocal started_count
            async with started_lock:
                started_count += 1
                if started_count == len(reviewers):
                    all_started.set()

            await release_reviewers.wait()
            return await batch.approve(reviewer)

        reviewer_tasks = [
            asyncio.create_task(approve(reviewer))
            for reviewer in reviewers
        ]
        await asyncio.wait_for(all_started.wait(), timeout=1)

        waiter = asyncio.create_task(batch.wait_until_approved(timeout=1))
        await asyncio.sleep(0)
        self.assertFalse(await batch.is_approved())
        self.assertFalse(waiter.done())

        release_reviewers.set()
        self.assertTrue(await asyncio.wait_for(waiter, timeout=1))
        self.assertEqual(
            await asyncio.gather(*reviewer_tasks),
            [True] * len(reviewers),
        )
        self.assertEqual(await batch.remaining_reviewers(), frozenset())


if __name__ == "__main__":
    unittest.main()
