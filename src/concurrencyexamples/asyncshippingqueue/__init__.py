"""Dispatch express shipments before economy shipments.

Use `asyncio.PriorityQueue` for async prioritized handoff to carrier workers.
"""

from concurrencyexamples.asyncshippingqueue.queue import (
    AsyncShippingQueue,
    ShipmentJob,
)

__all__ = ["AsyncShippingQueue", "ShipmentJob"]
