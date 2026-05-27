"""Apply duplicate payment webhooks only once.

Use `threading.Lock` to protect idempotency checks and payment totals during
concurrent webhook delivery.
"""

from python_concurrency_examples.examples.paymentwebhook.processor import (
    PaymentSummary,
    PaymentWebhookProcessor,
)

__all__ = ["PaymentSummary", "PaymentWebhookProcessor"]
