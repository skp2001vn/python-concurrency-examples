"""Unit tests for the fraudscorebatch example.

The example models CPU-bound fraud scoring for payment transactions. The tests
verify caller-facing behavior: invalid inputs are rejected, one transaction can
be scored directly, process-pool batches preserve input order, and worker-side
exceptions are propagated to the caller.
"""

import unittest

from concurrencyexamples.fraudscorebatch import (
    FraudScore,
    FraudScoreBatch,
    Transaction,
    score_transaction,
)


class FraudScoreBatchTest(unittest.TestCase):
    """FraudScoreBatchTest verifies the public fraud scoring behavior."""

    # Verifies that transaction IDs must be non-empty.
    def test_rejects_empty_transaction_id(self) -> None:
        with self.assertRaises(ValueError):
            Transaction(transaction_id="", amount_cents=1000, country="US")

    # Verifies that numeric transaction fields cannot be negative.
    def test_rejects_negative_transaction_fields(self) -> None:
        with self.assertRaises(ValueError):
            Transaction(transaction_id="txn-1", amount_cents=-1, country="US")
        with self.assertRaises(ValueError):
            Transaction(
                transaction_id="txn-1",
                amount_cents=1000,
                country="US",
                previous_chargebacks=-1,
            )
        with self.assertRaises(ValueError):
            Transaction(
                transaction_id="txn-1",
                amount_cents=1000,
                country="US",
                account_age_days=-1,
            )

    # Verifies that callers must choose a positive process limit.
    def test_rejects_invalid_worker_limit(self) -> None:
        with self.assertRaises(ValueError):
            FraudScoreBatch(max_workers=0)

    # Verifies that callers must provide at least one transaction.
    def test_rejects_empty_batch(self) -> None:
        batch = FraudScoreBatch(max_workers=1)

        with self.assertRaises(ValueError):
            batch.score_all([])

    # Verifies that one low-risk transaction is approved.
    def test_scores_low_risk_transaction(self) -> None:
        transaction = Transaction(
            transaction_id="txn-1",
            amount_cents=5000,
            country="US",
            account_age_days=90,
        )

        self.assertEqual(
            score_transaction(transaction),
            FraudScore(transaction_id="txn-1", score=0, decision="approve"),
        )

    # Verifies that higher-risk transaction signals produce review and decline.
    def test_scores_higher_risk_transactions(self) -> None:
        review_transaction = Transaction(
            transaction_id="txn-review",
            amount_cents=150_000,
            country="BR",
            account_age_days=10,
        )
        decline_transaction = Transaction(
            transaction_id="txn-decline",
            amount_cents=250_000,
            country="BR",
            previous_chargebacks=1,
            account_age_days=10,
        )

        self.assertEqual(score_transaction(review_transaction).decision, "review")
        self.assertEqual(score_transaction(decline_transaction).decision, "decline")

    # Verifies that process-pool batch results keep the caller's input order.
    def test_scores_batch_in_input_order(self) -> None:
        transactions = [
            Transaction(
                transaction_id="txn-approve",
                amount_cents=5000,
                country="US",
                account_age_days=90,
            ),
            Transaction(
                transaction_id="txn-review",
                amount_cents=150_000,
                country="BR",
                account_age_days=10,
            ),
            Transaction(
                transaction_id="txn-decline",
                amount_cents=250_000,
                country="BR",
                previous_chargebacks=1,
                account_age_days=10,
            ),
        ]
        batch = FraudScoreBatch(max_workers=2)

        results = batch.score_all(transactions)

        self.assertEqual(
            [result.transaction_id for result in results],
            ["txn-approve", "txn-review", "txn-decline"],
        )
        self.assertEqual(
            [result.decision for result in results],
            ["approve", "review", "decline"],
        )

    # Verifies that worker-side scoring errors are raised to the caller.
    def test_propagates_worker_exception(self) -> None:
        transactions = [
            Transaction(transaction_id="txn-1", amount_cents=1000, country="USA")
        ]
        batch = FraudScoreBatch(max_workers=1)

        with self.assertRaises(ValueError):
            batch.score_all(transactions)


if __name__ == "__main__":
    unittest.main()
