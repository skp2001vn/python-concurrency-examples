"""Track player scores for a leaderboard.

The business logic is a game, learning platform, or sales contest where many
worker threads record scores while other callers read the current leaders.

The example uses `threading.Lock` because score updates and sorted snapshots
must see a consistent shared dictionary. The lock protects all access to the
player score state.
"""

from dataclasses import dataclass
from threading import Lock


@dataclass(frozen=True, slots=True)
class ScoreEntry:
    """ScoreEntry reports one player's score in a leaderboard snapshot.

    Attributes:
        player_id: Stable identifier for the player.
        score: Best score recorded for the player.
    """

    player_id: str
    score: int


class Leaderboard:
    """Leaderboard records best scores and returns consistent rankings.

    The leaderboard is safe for concurrent use by many threads. Each player
    keeps their highest recorded score, and ranking snapshots are sorted by
    score descending with player ID as a deterministic tie breaker.
    """

    def __init__(self) -> None:
        """Create an empty leaderboard."""
        self._lock = Lock()
        self._scores: dict[str, int] = {}

    def record_score(self, player_id: str, score: int) -> None:
        """Record a player score, keeping the player's highest score."""
        if not player_id:
            raise ValueError("player_id must not be empty")
        if score < 0:
            raise ValueError("score must not be negative")

        with self._lock:
            previous_score = self._scores.get(player_id)
            if previous_score is None or score > previous_score:
                self._scores[player_id] = score

    def score_for(self, player_id: str) -> int | None:
        """Return a player's best score, or `None` if the player is unknown."""
        if not player_id:
            raise ValueError("player_id must not be empty")

        with self._lock:
            return self._scores.get(player_id)

    def top(self, limit: int) -> tuple[ScoreEntry, ...]:
        """Return a consistent top-ranking snapshot with at most `limit` entries."""
        if limit <= 0:
            raise ValueError("limit must be greater than zero")

        with self._lock:
            sorted_scores = sorted(
                self._scores.items(),
                key=lambda item: (-item[1], item[0]),
            )
            return tuple(
                ScoreEntry(player_id=player_id, score=score)
                for player_id, score in sorted_scores[:limit]
            )

    def snapshot(self) -> dict[str, int]:
        """Return a consistent copy of all player scores."""
        with self._lock:
            return dict(self._scores)
