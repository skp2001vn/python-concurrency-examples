"""Release an async review batch after required approvals arrive.

A batch of vendor changes, policy exceptions, or compliance documents needs
several async reviewers before it can be released. Different reviewer tasks
approve independently, and request tasks wait until the whole batch is ready.

The example uses `asyncio.Condition` because approvals update shared state and
waiting tasks need to suspend until that state satisfies the approval rule. The
condition protects the approval set and wakes waiters without polling.
"""

import asyncio
from collections.abc import Iterable


class AsyncReviewBatch:
    """AsyncReviewBatch tracks required reviewers for one async business batch.

    The approval state is safe for concurrent use by many tasks in the same
    event loop. Approval calls validate reviewers, duplicate approvals leave
    state unchanged, and waiters suspend until every required reviewer has
    approved or a timeout expires.
    """

    def __init__(self, required_reviewers: Iterable[str]) -> None:
        """Create a review batch that requires each named reviewer."""
        reviewers = frozenset(required_reviewers)
        if not reviewers:
            raise ValueError("required_reviewers must not be empty")
        if any(not reviewer for reviewer in reviewers):
            raise ValueError("reviewer names must not be empty")

        self._condition = asyncio.Condition()
        self._required_reviewers = reviewers
        self._approved_reviewers: set[str] = set()

    async def approve(self, reviewer: str) -> bool:
        """Record one reviewer approval and return whether state changed."""
        if not reviewer:
            raise ValueError("reviewer name must not be empty")

        async with self._condition:
            if reviewer not in self._required_reviewers:
                raise ValueError(f"{reviewer!r} is not a required reviewer")
            if reviewer in self._approved_reviewers:
                return False

            self._approved_reviewers.add(reviewer)
            self._condition.notify_all()
            return True

    async def wait_until_approved(self, timeout: float | None = None) -> bool:
        """Suspend until all required reviewers approve or timeout expires."""
        if timeout is not None and timeout < 0:
            raise ValueError("timeout must not be negative")

        async with self._condition:
            if self._is_approved():
                return True

            try:
                if timeout is None:
                    await self._condition.wait_for(self._is_approved)
                else:
                    await asyncio.wait_for(
                        self._condition.wait_for(self._is_approved),
                        timeout=timeout,
                    )
            except TimeoutError:
                return False

            return True

    async def is_approved(self) -> bool:
        """Return whether every required reviewer has approved the batch."""
        async with self._condition:
            return self._is_approved()

    async def approved_by(self) -> frozenset[str]:
        """Return the reviewers who have approved so far."""
        async with self._condition:
            return frozenset(self._approved_reviewers)

    async def remaining_reviewers(self) -> frozenset[str]:
        """Return the required reviewers who have not approved yet."""
        async with self._condition:
            return self._required_reviewers - self._approved_reviewers

    def _is_approved(self) -> bool:
        return self._required_reviewers <= self._approved_reviewers
