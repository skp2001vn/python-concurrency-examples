"""Score CPU-heavy transaction fraud risk in parallel.

The business logic is a fraud review workflow: a payment system receives many
transactions and each one needs a CPU-heavy risk score before it can be
approved, reviewed, or declined.

The example uses `concurrent.futures.ProcessPoolExecutor` because fraud scoring
can be CPU-bound, and CPU-bound Python threads are limited by the GIL. Separate
worker processes can run independent scoring jobs on multiple CPU cores. The
worker function is defined at module level so it can be pickled and executed in
child processes.
"""

from collections.abc import Iterable
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from typing import Literal

FraudDecision = Literal["approve", "review", "decline"]

_LOW_RISK_COUNTRIES = frozenset({"CA", "GB", "US"})


@dataclass(frozen=True, slots=True)
class Transaction:
    """Transaction describes one payment that needs fraud scoring.

    Attributes:
        transaction_id: Stable business identifier for the transaction.
        amount_cents: Payment amount in cents.
        country: Two-letter country code for the payment origin.
        previous_chargebacks: Number of previous chargebacks for the customer.
        account_age_days: Age of the customer account in days.
    """

    transaction_id: str
    amount_cents: int
    country: str
    previous_chargebacks: int = 0
    account_age_days: int = 0

    def __post_init__(self) -> None:
        """Validate transaction fields that should never be negative or empty."""
        if not self.transaction_id:
            raise ValueError("transaction_id must not be empty")
        if self.amount_cents < 0:
            raise ValueError("amount_cents must not be negative")
        if not self.country:
            raise ValueError("country must not be empty")
        if self.previous_chargebacks < 0:
            raise ValueError("previous_chargebacks must not be negative")
        if self.account_age_days < 0:
            raise ValueError("account_age_days must not be negative")


@dataclass(frozen=True, slots=True)
class FraudScore:
    """FraudScore reports the risk score and decision for one transaction.

    Attributes:
        transaction_id: Stable business identifier for the scored transaction.
        score: Fraud risk score from 0 to 100.
        decision: Caller-facing fraud decision derived from the score.
    """

    transaction_id: str
    score: int
    decision: FraudDecision


class FraudScoreBatch:
    """FraudScoreBatch scores CPU-bound transactions in worker processes.

    The process pool lets independent scoring jobs run across CPU cores while
    preserving input order in the returned scores. Exceptions raised while
    scoring a transaction are propagated when the caller collects the batch
    result.
    """

    def __init__(self, max_workers: int | None = None) -> None:
        """Create a fraud score batcher with an optional process limit."""
        if max_workers is not None and max_workers <= 0:
            raise ValueError("max_workers must be greater than zero")

        self._max_workers = max_workers

    def score_all(self, transactions: Iterable[Transaction]) -> tuple[FraudScore, ...]:
        """Score all transactions in parallel and return results in input order."""
        transaction_batch = tuple(transactions)
        if not transaction_batch:
            raise ValueError("transactions must not be empty")

        with ProcessPoolExecutor(max_workers=self._max_workers) as executor:
            return tuple(executor.map(score_transaction, transaction_batch))


def score_transaction(transaction: Transaction) -> FraudScore:
    """Score one transaction and return its fraud decision.

    This function is intentionally module-level so `ProcessPoolExecutor` can
    pickle it and run it in a worker process.
    """
    _validate_country_code(transaction.country)

    score = min(transaction.amount_cents // 10_000, 35)
    score += min(transaction.previous_chargebacks * 25, 50)
    if transaction.country not in _LOW_RISK_COUNTRIES:
        score += 20
    if transaction.account_age_days < 30:
        score += 15

    score = min(score, 100)
    return FraudScore(
        transaction_id=transaction.transaction_id,
        score=score,
        decision=_decision_for(score),
    )


def _validate_country_code(country: str) -> None:
    if len(country) != 2 or not country.isalpha() or country != country.upper():
        raise ValueError("country must be a two-letter uppercase country code")


def _decision_for(score: int) -> FraudDecision:
    if score >= 70:
        return "decline"
    if score >= 40:
        return "review"
    return "approve"
