"""Apply duplicate payment webhooks only once.

Use `threading.Lock` to protect idempotency checks and payment totals during
concurrent webhook delivery.
"""

from concurrencyexamples.paymentwebhook.processor import (
    PaymentSummary,
    PaymentWebhookProcessor,
)

__all__ = ["PaymentSummary", "PaymentWebhookProcessor"]
