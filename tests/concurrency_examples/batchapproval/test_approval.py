"""Unit tests for the batchapproval example.

The example models documents, expenses, or account changes that need several
approvals before release. The tests verify caller-facing behavior: required
reviewers are validated, approvals are idempotent, waiters can time out, and
worker threads can release waiting callers by completing the approval set.
"""

import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event

from concurrency_examples.batchapproval import BatchApproval


class BatchApprovalTest(unittest.TestCase):
    """BatchApprovalTest verifies the public behavior of batch approvals."""

    # Verifies that callers must configure at least one reviewer.
    def test_rejects_empty_reviewer_set(self) -> None:
        with self.assertRaises(ValueError):
            BatchApproval([])

    # Verifies that blank reviewer names are not valid configuration.
    def test_rejects_blank_reviewer_names(self) -> None:
        with self.assertRaises(ValueError):
            BatchApproval(["finance", ""])

    # Verifies that each required reviewer can approve exactly once.
    def test_records_required_approvals(self) -> None:
        batch = BatchApproval(["finance", "legal"])

        self.assertTrue(batch.approve("finance"))
        self.assertFalse(batch.approve("finance"))
        self.assertFalse(batch.is_approved())
        self.assertEqual(batch.approved_by(), frozenset({"finance"}))
        self.assertEqual(batch.remaining_reviewers(), frozenset({"legal"}))

        self.assertTrue(batch.approve("legal"))

        self.assertTrue(batch.is_approved())
        self.assertEqual(batch.remaining_reviewers(), frozenset())

    # Verifies that callers cannot approve with a reviewer outside the batch.
    def test_rejects_unexpected_reviewer(self) -> None:
        batch = BatchApproval(["finance"])

        with self.assertRaises(ValueError):
            batch.approve("manager")

        self.assertEqual(batch.approved_by(), frozenset())

    # Verifies that waiters return immediately when the batch is already approved.
    def test_wait_returns_true_when_already_approved(self) -> None:
        batch = BatchApproval(["finance"])
        batch.approve("finance")

        self.assertTrue(batch.wait_until_approved(timeout=0))

    # Verifies that waiters can time out while approvals are incomplete.
    def test_wait_returns_false_on_timeout(self) -> None:
        batch = BatchApproval(["finance", "legal"])
        batch.approve("finance")

        self.assertFalse(batch.wait_until_approved(timeout=0.01))

    # Verifies that another caller waits until all reviewer threads approve.
    def test_waiter_returns_after_whole_batch_is_approved(self) -> None:
        reviewers = ["finance", "legal", "manager"]
        batch = BatchApproval(reviewers)
        approvers_ready = Barrier(len(reviewers) + 1)
        release_approvers = Event()

        def approve(reviewer: str) -> bool:
            approvers_ready.wait(timeout=1)
            if not release_approvers.wait(timeout=1):
                raise AssertionError("timed out waiting to approve")
            return batch.approve(reviewer)

        with ThreadPoolExecutor(max_workers=len(reviewers) + 1) as executor:
            futures = [executor.submit(approve, reviewer) for reviewer in reviewers]
            approvers_ready.wait(timeout=1)
            waiter = executor.submit(batch.wait_until_approved, 1)

            self.assertFalse(batch.is_approved())
            release_approvers.set()
            self.assertTrue(waiter.result(timeout=1))
            self.assertEqual(
                [future.result(timeout=1) for future in futures],
                [True] * 3,
            )

        self.assertEqual(batch.approved_by(), frozenset(reviewers))


if __name__ == "__main__":
    unittest.main()
