"""Dispatch express shipments before economy shipments.

The business logic is an async fulfillment workflow: checkout tasks submit
shipment jobs, while async carrier-worker tasks dispatch the next shipment.
Express shipments should be sent before economy shipments.

The example uses `asyncio.PriorityQueue` because async producers and workers
need a coroutine-safe priority handoff point. Lower priority numbers are
dispatched first, and a sequence number keeps same-priority shipments in submit
order.
"""

import asyncio
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ShipmentJob:
    """ShipmentJob describes one package waiting for carrier dispatch.

    Attributes:
        shipment_id: Stable identifier for the shipment.
        order_id: Stable identifier for the customer order.
        priority: Dispatch priority where lower numbers are more urgent.
        carrier: Carrier name selected for the shipment.
    """

    shipment_id: str
    order_id: str
    priority: int
    carrier: str

    def __post_init__(self) -> None:
        """Validate shipment fields required for prioritized dispatch."""
        if not self.shipment_id:
            raise ValueError("shipment_id must not be empty")
        if not self.order_id:
            raise ValueError("order_id must not be empty")
        if self.priority < 0:
            raise ValueError("priority must not be negative")
        if not self.carrier:
            raise ValueError("carrier must not be empty")


class AsyncShippingQueue:
    """AsyncShippingQueue hands prioritized shipments to async workers.

    The queue is safe for concurrent use by many tasks in the same event loop.
    Producers submit shipment jobs, carrier workers dispatch the most urgent
    pending job, and callers can time out instead of waiting forever.
    """

    def __init__(self) -> None:
        """Create an empty async shipping queue."""
        self._queue: asyncio.PriorityQueue[tuple[int, int, ShipmentJob]]
        self._queue = asyncio.PriorityQueue()
        self._sequence_lock = asyncio.Lock()
        self._next_sequence = 0

    async def submit(self, job: ShipmentJob) -> None:
        """Submit one shipment for prioritized dispatch."""
        async with self._sequence_lock:
            sequence = self._next_sequence
            self._next_sequence += 1

        await self._queue.put((job.priority, sequence, job))

    async def dispatch_next(self, timeout: float | None = None) -> ShipmentJob | None:
        """Wait for the next shipment, or return `None` when timeout expires."""
        if timeout is not None and timeout < 0:
            raise ValueError("timeout must not be negative")

        try:
            if timeout is None:
                _, _, job = await self._queue.get()
            else:
                _, _, job = await asyncio.wait_for(
                    self._queue.get(),
                    timeout=timeout,
                )
        except TimeoutError:
            return None

        return job

    def task_done(self) -> None:
        """Mark one previously dispatched shipment as handled."""
        self._queue.task_done()

    async def join(self) -> None:
        """Wait until all dispatched shipments have been marked as handled."""
        await self._queue.join()

    def size(self) -> int:
        """Return the approximate number of waiting shipments."""
        return self._queue.qsize()
