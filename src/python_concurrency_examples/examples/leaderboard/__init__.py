"""Track player scores for a leaderboard.

Use `threading.Lock` to protect score updates and top-ranking snapshots.
"""

from python_concurrency_examples.examples.leaderboard.scores import (
    Leaderboard,
    ScoreEntry,
)

__all__ = ["Leaderboard", "ScoreEntry"]
