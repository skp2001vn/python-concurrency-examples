"""Apply duplicate payment webhooks only once.

The business logic is a payment webhook workflow: a payment processor may
deliver the same event more than once, and several worker threads may process
webhook deliveries concurrently.

The example uses `threading.Lock` because each event must be checked for
idempotency and then applied as one atomic operation. The lock protects both
the processed event IDs and the payment totals.
"""

from dataclasses import dataclass
from threading import Lock


@dataclass(frozen=True, slots=True)
class PaymentSummary:
    """PaymentSummary reports payment webhook totals at one moment in time.

    Attributes:
        processed_events: Number of unique payment events that were applied.
        total_cents: Total payment amount from unique applied events.
    """

    processed_events: int = 0
    total_cents: int = 0


class PaymentWebhookProcessor:
    """PaymentWebhookProcessor applies each payment event at most once.

    The processor is safe for concurrent use by many threads. Duplicate event
    IDs are ignored, new event IDs update totals exactly once, and callers can
    read a consistent summary of applied payments.
    """

    def __init__(self) -> None:
        """Create a processor with no applied payment events."""
        self._lock = Lock()
        self._processed_event_ids: set[str] = set()
        self._total_cents = 0

    def process(self, event_id: str, amount_cents: int) -> bool:
        """Apply a payment event and return whether it changed totals."""
        if not event_id:
            raise ValueError("event_id must not be empty")
        if amount_cents <= 0:
            raise ValueError("amount_cents must be greater than zero")

        with self._lock:
            if event_id in self._processed_event_ids:
                return False

            self._processed_event_ids.add(event_id)
            self._total_cents += amount_cents
            return True

    def summary(self) -> PaymentSummary:
        """Return a consistent snapshot of applied payment totals."""
        with self._lock:
            return PaymentSummary(
                processed_events=len(self._processed_event_ids),
                total_cents=self._total_cents,
            )

    def processed_event_ids(self) -> frozenset[str]:
        """Return the unique payment event IDs applied so far."""
        with self._lock:
            return frozenset(self._processed_event_ids)
