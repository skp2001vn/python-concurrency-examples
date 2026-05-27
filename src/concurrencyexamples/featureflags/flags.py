"""Read and refresh an in-memory feature flag snapshot.

The business logic is a service configuration workflow: request threads read
feature flags constantly, while an admin or refresh thread occasionally
replaces the whole flag snapshot.

The example uses `threading.RLock` because public read operations can call other
lock-protected helpers without deadlocking. The lock keeps snapshot reads and
refreshes consistent for all threads.
"""

from collections.abc import Mapping
from threading import RLock


class FeatureFlags:
    """FeatureFlags stores a thread-safe in-memory flag snapshot.

    The flag snapshot is safe for concurrent use by many threads. Missing flags
    default to disabled, refresh replaces the entire snapshot atomically, and
    nested read helpers can reuse the same reentrant lock.
    """

    def __init__(self, flags: Mapping[str, bool]) -> None:
        """Create a feature flag snapshot from flag names to enabled values."""
        self._validate_flags(flags)
        self._lock = RLock()
        self._flags = dict(flags)

    def is_enabled(self, name: str) -> bool:
        """Return whether a feature flag is currently enabled."""
        if not name:
            raise ValueError("flag name must not be empty")

        with self._lock:
            return self._flags.get(name, False)

    def replace_all(self, flags: Mapping[str, bool]) -> None:
        """Atomically replace the full feature flag snapshot."""
        self._validate_flags(flags)

        with self._lock:
            self._flags = dict(flags)

    def enabled_flags(self) -> frozenset[str]:
        """Return names for all currently enabled feature flags."""
        with self._lock:
            return frozenset(
                name
                for name in self._flags
                if self.is_enabled(name)
            )

    def snapshot(self) -> dict[str, bool]:
        """Return a consistent copy of all current feature flags."""
        with self._lock:
            return self._flags.copy()

    def _validate_flags(self, flags: Mapping[str, bool]) -> None:
        if any(not name for name in flags):
            raise ValueError("flag names must not be empty")
