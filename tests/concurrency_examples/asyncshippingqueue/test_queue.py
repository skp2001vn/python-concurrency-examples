"""Unit tests for the asyncshippingqueue example.

The example models async checkout tasks submitting shipment jobs and carrier
workers dispatching them by priority. The tests verify caller-facing behavior:
invalid shipments are rejected, express shipments dispatch first,
same-priority shipments keep submit order, empty waits can time out, and
concurrent workers dispatch each shipment at most once.
"""

import asyncio
import unittest

from concurrency_examples.asyncshippingqueue import (
    AsyncShippingQueue,
    ShipmentJob,
)


class AsyncShippingQueueTest(unittest.IsolatedAsyncioTestCase):
    """AsyncShippingQueueTest verifies the public async priority queue behavior."""

    # Verifies that shipment IDs must be non-empty.
    async def test_rejects_empty_shipment_id(self) -> None:
        with self.assertRaises(ValueError):
            ShipmentJob(
                shipment_id="",
                order_id="order-1",
                priority=1,
                carrier="carrier-a",
            )

    # Verifies that order IDs must be non-empty.
    async def test_rejects_empty_order_id(self) -> None:
        with self.assertRaises(ValueError):
            ShipmentJob(
                shipment_id="shipment-1",
                order_id="",
                priority=1,
                carrier="carrier-a",
            )

    # Verifies that dispatch priorities cannot be negative.
    async def test_rejects_negative_priority(self) -> None:
        with self.assertRaises(ValueError):
            ShipmentJob(
                shipment_id="shipment-1",
                order_id="order-1",
                priority=-1,
                carrier="carrier-a",
            )

    # Verifies that carrier names must be non-empty.
    async def test_rejects_empty_carrier(self) -> None:
        with self.assertRaises(ValueError):
            ShipmentJob(
                shipment_id="shipment-1",
                order_id="order-1",
                priority=1,
                carrier="",
            )

    # Verifies that workers dispatch express shipments before economy shipments.
    async def test_dispatches_lower_priority_number_first(self) -> None:
        queue = AsyncShippingQueue()
        economy = self.shipment("economy", priority=5)
        express = self.shipment("express", priority=0)

        await queue.submit(economy)
        await queue.submit(express)

        self.assertEqual(await queue.dispatch_next(timeout=1), express)
        queue.task_done()
        self.assertEqual(await queue.dispatch_next(timeout=1), economy)
        queue.task_done()
        await queue.join()

    # Verifies that same-priority shipments keep submit order.
    async def test_dispatches_same_priority_shipments_in_submit_order(self) -> None:
        queue = AsyncShippingQueue()
        first = self.shipment("first", priority=2)
        second = self.shipment("second", priority=2)

        await queue.submit(first)
        await queue.submit(second)

        self.assertEqual(await queue.dispatch_next(timeout=1), first)
        queue.task_done()
        self.assertEqual(await queue.dispatch_next(timeout=1), second)
        queue.task_done()
        await queue.join()

    # Verifies that workers can time out instead of waiting forever.
    async def test_dispatch_next_returns_none_on_timeout(self) -> None:
        queue = AsyncShippingQueue()

        self.assertIsNone(await queue.dispatch_next(timeout=0.01))

    # Verifies that negative timeout values are rejected.
    async def test_rejects_negative_timeout(self) -> None:
        queue = AsyncShippingQueue()

        with self.assertRaises(ValueError):
            await queue.dispatch_next(timeout=-1)

    # Verifies that async producers can submit all shipments safely.
    async def test_concurrent_producers_submit_all_shipments(self) -> None:
        shipment_count = 50
        queue = AsyncShippingQueue()

        await asyncio.gather(
            *(
                queue.submit(self.shipment(f"shipment-{index}", priority=index % 5))
                for index in range(shipment_count)
            )
        )

        dispatched_shipment_ids = set()
        for _ in range(shipment_count):
            job = await queue.dispatch_next(timeout=1)
            self.assertIsNotNone(job)
            dispatched_shipment_ids.add(job.shipment_id)
            queue.task_done()

        await queue.join()
        self.assertEqual(
            dispatched_shipment_ids,
            {f"shipment-{index}" for index in range(shipment_count)},
        )
        self.assertEqual(queue.size(), 0)

    # Verifies that concurrent carrier workers dispatch each shipment once.
    async def test_concurrent_workers_dispatch_each_shipment_once(self) -> None:
        shipment_count = 80
        worker_count = 6
        queue = AsyncShippingQueue()
        dispatched_shipment_ids: list[str] = []
        dispatched_lock = asyncio.Lock()

        for index in range(shipment_count):
            await queue.submit(self.shipment(f"shipment-{index}", priority=index % 4))

        async def dispatch_shipments() -> None:
            while job := await queue.dispatch_next(timeout=0.01):
                try:
                    async with dispatched_lock:
                        dispatched_shipment_ids.append(job.shipment_id)
                finally:
                    queue.task_done()

        await asyncio.gather(*(dispatch_shipments() for _ in range(worker_count)))
        await queue.join()

        self.assertEqual(len(dispatched_shipment_ids), shipment_count)
        self.assertEqual(
            set(dispatched_shipment_ids),
            {f"shipment-{index}" for index in range(shipment_count)},
        )
        self.assertEqual(len(set(dispatched_shipment_ids)), shipment_count)

    # Verifies that a worker waits until a later producer submits a shipment.
    async def test_dispatch_next_waits_for_later_submission(self) -> None:
        queue = AsyncShippingQueue()
        waiter = asyncio.create_task(queue.dispatch_next(timeout=1))

        await asyncio.sleep(0)
        self.assertFalse(waiter.done())

        shipment = self.shipment("express", priority=0)
        await queue.submit(shipment)

        self.assertEqual(await waiter, shipment)
        queue.task_done()
        await queue.join()

    def shipment(self, shipment_id: str, priority: int) -> ShipmentJob:
        """Create one valid shipment job for tests."""
        return ShipmentJob(
            shipment_id=shipment_id,
            order_id=f"order-{shipment_id}",
            priority=priority,
            carrier="carrier-a",
        )


if __name__ == "__main__":
    unittest.main()
