"""Unit tests for the leaderboard example.

The example models score updates from many worker threads. The tests verify
caller-facing behavior: invalid scores are rejected, each player keeps their
best score, top rankings are deterministic snapshots, and concurrent updates
do not corrupt shared state.
"""

import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from concurrencyexamples.leaderboard import (
    Leaderboard,
    ScoreEntry,
)


class LeaderboardTest(unittest.TestCase):
    """LeaderboardTest verifies the public leaderboard behavior."""

    # Verifies that player IDs must be non-empty when recording scores.
    def test_rejects_blank_player_id_for_record_score(self) -> None:
        leaderboard = Leaderboard()

        with self.assertRaises(ValueError):
            leaderboard.record_score("", score=10)

    # Verifies that score lookups require a non-empty player ID.
    def test_rejects_blank_player_id_for_score_lookup(self) -> None:
        leaderboard = Leaderboard()

        with self.assertRaises(ValueError):
            leaderboard.score_for("")

    # Verifies that scores cannot be negative.
    def test_rejects_negative_score(self) -> None:
        leaderboard = Leaderboard()

        with self.assertRaises(ValueError):
            leaderboard.record_score("player-1", score=-1)

    # Verifies that top rankings require a positive limit.
    def test_rejects_non_positive_top_limit(self) -> None:
        leaderboard = Leaderboard()

        with self.assertRaises(ValueError):
            leaderboard.top(0)

    # Verifies that callers can record and read player scores.
    def test_records_and_returns_score(self) -> None:
        leaderboard = Leaderboard()

        leaderboard.record_score("alice", score=40)
        leaderboard.record_score("bob", score=25)

        self.assertEqual(leaderboard.score_for("alice"), 40)
        self.assertEqual(leaderboard.score_for("bob"), 25)
        self.assertIsNone(leaderboard.score_for("carol"))

    # Verifies that a lower later score does not replace a player's best score.
    def test_keeps_highest_score_per_player(self) -> None:
        leaderboard = Leaderboard()

        leaderboard.record_score("alice", score=40)
        leaderboard.record_score("alice", score=30)
        leaderboard.record_score("alice", score=45)

        self.assertEqual(leaderboard.score_for("alice"), 45)

    # Verifies that rankings are sorted by score and use player ID for ties.
    def test_returns_top_players_in_deterministic_order(self) -> None:
        leaderboard = Leaderboard()

        leaderboard.record_score("carol", score=50)
        leaderboard.record_score("alice", score=70)
        leaderboard.record_score("bob", score=70)
        leaderboard.record_score("dave", score=20)

        self.assertEqual(
            leaderboard.top(3),
            (
                ScoreEntry(player_id="alice", score=70),
                ScoreEntry(player_id="bob", score=70),
                ScoreEntry(player_id="carol", score=50),
            ),
        )

    # Verifies that top rankings are snapshots independent from later updates.
    def test_top_returns_independent_snapshot(self) -> None:
        leaderboard = Leaderboard()
        leaderboard.record_score("alice", score=40)

        first_snapshot = leaderboard.top(1)
        leaderboard.record_score("alice", score=80)

        self.assertEqual(first_snapshot, (ScoreEntry(player_id="alice", score=40),))
        self.assertEqual(
            leaderboard.top(1),
            (ScoreEntry(player_id="alice", score=80),),
        )

    # Verifies that concurrent score updates leave one best score per player.
    def test_concurrent_updates_keep_best_scores(self) -> None:
        player_count = 20
        scores_per_player = 5
        leaderboard = Leaderboard()
        ready = Barrier(player_count + 1)

        def record_scores(player_index: int) -> None:
            ready.wait(timeout=1)
            player_id = f"player-{player_index:02d}"
            for score in range(scores_per_player):
                leaderboard.record_score(player_id, score=score)

        with ThreadPoolExecutor(max_workers=player_count) as executor:
            futures = [
                executor.submit(record_scores, player_index)
                for player_index in range(player_count)
            ]
            ready.wait(timeout=1)
            for future in futures:
                future.result(timeout=1)

        expected_best_score = scores_per_player - 1
        self.assertEqual(len(leaderboard.snapshot()), player_count)
        self.assertTrue(
            all(
                entry.score == expected_best_score
                for entry in leaderboard.top(player_count)
            )
        )


if __name__ == "__main__":
    unittest.main()
