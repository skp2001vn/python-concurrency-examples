"""Wait for async payment completion from request tasks.

The business logic is an async checkout workflow: one task processes a payment
while several request tasks may wait for the final success or failure result.

The example uses `asyncio.Event` because payment completion is a one-shot
signal that should wake every current waiter and let later waiters return
immediately. Each payment owns its own event and result state.
"""

import asyncio
from dataclasses import dataclass
from typing import Literal

PaymentOutcome = Literal["succeeded", "failed"]


@dataclass(frozen=True, slots=True)
class PaymentResult:
    """PaymentResult reports the final outcome for one payment.

    Attributes:
        payment_id: Stable identifier for the payment.
        outcome: Final payment outcome.
        reason: Failure reason, or `None` when the payment succeeded.
    """

    payment_id: str
    outcome: PaymentOutcome
    reason: str | None = None


@dataclass(slots=True)
class _PaymentState:
    event: asyncio.Event
    result: PaymentResult | None = None


class AsyncPaymentStatus:
    """AsyncPaymentStatus publishes one payment result to many waiters.

    The status tracker is safe for concurrent use by many tasks in the same
    event loop. The first success or failure result for a payment wins, all
    waiters observe the same result, and callers may wait with a timeout.
    """

    def __init__(self) -> None:
        """Create an empty payment status tracker."""
        self._states: dict[str, _PaymentState] = {}

    async def mark_succeeded(self, payment_id: str) -> bool:
        """Record payment success and return whether this completed the payment."""
        self._validate_payment_id(payment_id)

        state = self._state_for(payment_id)
        if state.result is not None:
            return False

        state.result = PaymentResult(payment_id=payment_id, outcome="succeeded")
        state.event.set()
        return True

    async def mark_failed(self, payment_id: str, reason: str) -> bool:
        """Record payment failure and return whether this completed the payment."""
        self._validate_payment_id(payment_id)
        if not reason:
            raise ValueError("reason must not be empty")

        state = self._state_for(payment_id)
        if state.result is not None:
            return False

        state.result = PaymentResult(
            payment_id=payment_id,
            outcome="failed",
            reason=reason,
        )
        state.event.set()
        return True

    async def wait_for_result(
        self,
        payment_id: str,
        timeout: float | None = None,
    ) -> PaymentResult:
        """Wait for one payment result, raising `TimeoutError` when timeout expires."""
        self._validate_payment_id(payment_id)
        if timeout is not None and timeout < 0:
            raise ValueError("timeout must not be negative")

        state = self._state_for(payment_id)
        await asyncio.wait_for(state.event.wait(), timeout=timeout)
        if state.result is None:
            raise RuntimeError("payment event was set without a result")
        return state.result

    def result_for(self, payment_id: str) -> PaymentResult | None:
        """Return a payment result without waiting, or `None` if still pending."""
        self._validate_payment_id(payment_id)

        state = self._states.get(payment_id)
        if state is None:
            return None
        return state.result

    def _state_for(self, payment_id: str) -> _PaymentState:
        state = self._states.get(payment_id)
        if state is None:
            state = _PaymentState(event=asyncio.Event())
            self._states[payment_id] = state
        return state

    def _validate_payment_id(self, payment_id: str) -> None:
        if not payment_id:
            raise ValueError("payment_id must not be empty")
