"""Dispatch express shipments before economy shipments.

Use `asyncio.PriorityQueue` for async prioritized handoff to carrier workers.
"""

from python_concurrency_examples.examples.asyncshippingqueue.queue import (
    AsyncShippingQueue,
    ShipmentJob,
)

__all__ = ["AsyncShippingQueue", "ShipmentJob"]
