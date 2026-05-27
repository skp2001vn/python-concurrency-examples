"""Score CPU-heavy transaction fraud risk in parallel.

Use `ProcessPoolExecutor` to run scoring work on multiple CPU cores instead of
being limited by the GIL in worker threads.
"""

from concurrencyexamples.fraudscorebatch.scoring import (
    FraudDecision,
    FraudScore,
    FraudScoreBatch,
    Transaction,
    score_transaction,
)

__all__ = [
    "FraudDecision",
    "FraudScore",
    "FraudScoreBatch",
    "Transaction",
    "score_transaction",
]
