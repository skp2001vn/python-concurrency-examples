"""Read and refresh an in-memory feature flag snapshot.

Use `threading.RLock` for nested lock-protected operations over service
configuration.
"""

from concurrencyexamples.featureflags.flags import FeatureFlags

__all__ = ["FeatureFlags"]
