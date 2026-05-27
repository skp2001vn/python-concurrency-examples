"""Track player scores for a leaderboard.

Use `threading.Lock` to protect score updates and top-ranking snapshots.
"""

from concurrency_examples.leaderboard.scores import (
    Leaderboard,
    ScoreEntry,
)

__all__ = ["Leaderboard", "ScoreEntry"]
