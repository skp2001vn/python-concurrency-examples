"""Release a business batch after all required reviewers approve it.

A batch of documents, expenses, or account changes needs several approvals
before it can be released. Different reviewer threads approve items
independently, and another caller waits until the whole batch is approved.

The example uses `threading.Condition` because approvals update shared state and
waiting callers need to sleep until that state satisfies the approval rule.
"""

from collections.abc import Iterable
from threading import Condition


class BatchApproval:
    """BatchApproval tracks required reviewers for one business batch.

    The approval state is safe for concurrent use by many threads. Approval
    calls validate reviewers, duplicate approvals leave state unchanged, and
    waiters block until every required reviewer has approved or a timeout
    expires.
    """

    def __init__(self, required_reviewers: Iterable[str]) -> None:
        """Create a batch that requires approval from each named reviewer."""
        reviewers = frozenset(required_reviewers)
        if not reviewers:
            raise ValueError("required_reviewers must not be empty")
        if any(not reviewer for reviewer in reviewers):
            raise ValueError("reviewer names must not be empty")

        self._condition = Condition()
        self._required_reviewers = reviewers
        self._approved_reviewers: set[str] = set()

    def approve(self, reviewer: str) -> bool:
        """Record one reviewer approval and return whether state changed."""
        if not reviewer:
            raise ValueError("reviewer name must not be empty")

        with self._condition:
            if reviewer not in self._required_reviewers:
                raise ValueError(f"{reviewer!r} is not a required reviewer")
            if reviewer in self._approved_reviewers:
                return False

            self._approved_reviewers.add(reviewer)
            self._condition.notify_all()
            return True

    def wait_until_approved(self, timeout: float | None = None) -> bool:
        """Block until all required reviewers approve or timeout expires."""
        with self._condition:
            return self._condition.wait_for(self._is_approved, timeout=timeout)

    def is_approved(self) -> bool:
        """Return whether every required reviewer has approved the batch."""
        with self._condition:
            return self._is_approved()

    def approved_by(self) -> frozenset[str]:
        """Return the reviewers who have approved so far."""
        with self._condition:
            return frozenset(self._approved_reviewers)

    def remaining_reviewers(self) -> frozenset[str]:
        """Return the required reviewers who have not approved yet."""
        with self._condition:
            return self._required_reviewers - self._approved_reviewers

    def _is_approved(self) -> bool:
        return self._required_reviewers <= self._approved_reviewers
