"""Limit simultaneous third-party API calls.

Use `threading.BoundedSemaphore` to lease request permits and release them
safely when each API call finishes or fails.
"""

from concurrencyexamples.ratelimiter.limiter import ApiRateLimiter

__all__ = ["ApiRateLimiter"]
