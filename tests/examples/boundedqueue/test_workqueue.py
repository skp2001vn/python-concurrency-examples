"""Unit tests for the boundedqueue example.

The tests verify caller-facing behavior: bounded capacity is required, items
are handed off in order, timeout and shutdown exceptions come from the standard
queue API, and producer/consumer threads can coordinate through the queue.
"""

import unittest
from concurrent.futures import ThreadPoolExecutor
from queue import Empty, Full, ShutDown
from threading import Lock

from python_concurrency_examples.examples.boundedqueue import BoundedQueue


class BoundedQueueTest(unittest.TestCase):
    """BoundedQueueTest verifies the public behavior of the work queue."""

    # Verifies that callers must choose a positive queue capacity.
    def test_rejects_invalid_capacity(self) -> None:
        with self.assertRaises(ValueError):
            BoundedQueue[int](0)

    # Verifies that callers receive items in the order producers submitted them.
    def test_returns_items_in_fifo_order(self) -> None:
        queue = BoundedQueue[str](capacity=2)

        queue.put("first")
        queue.put("second")

        self.assertEqual(queue.get(), "first")
        queue.task_done()
        self.assertEqual(queue.get(), "second")
        queue.task_done()
        queue.join()

    # Verifies that consumers can time out instead of blocking forever.
    def test_get_times_out_when_empty(self) -> None:
        queue = BoundedQueue[int](capacity=1)

        with self.assertRaises(Empty):
            queue.get(timeout=0.01)

    # Verifies that producers can time out when the queue is at capacity.
    def test_put_times_out_when_full(self) -> None:
        queue = BoundedQueue[int](capacity=1)

        queue.put(1)
        with self.assertRaises(Full):
            queue.put(2, timeout=0.01)

    # Verifies that shutdown rejects producers while consumers drain pending work.
    def test_shutdown_rejects_new_work_after_pending_items_drain(self) -> None:
        queue = BoundedQueue[int](capacity=2)

        queue.put(1)
        queue.shutdown()

        with self.assertRaises(ShutDown):
            queue.put(2)
        self.assertEqual(queue.get(), 1)
        queue.task_done()
        with self.assertRaises(ShutDown):
            queue.get()
        queue.join()

    # Verifies that immediate shutdown discards pending work and unblocks join.
    def test_immediate_shutdown_discards_pending_work(self) -> None:
        queue = BoundedQueue[int](capacity=2)

        queue.put(1)
        queue.shutdown(immediate=True)

        with self.assertRaises(ShutDown):
            queue.get()
        queue.join()

    # Verifies that producer and consumer threads safely hand off all work.
    def test_hands_work_between_producers_and_consumers(self) -> None:
        producer_count = 4
        consumer_count = 4
        items_per_producer = 25
        total_items = producer_count * items_per_producer
        queue = BoundedQueue[int](capacity=3)
        processed: list[int] = []
        processed_lock = Lock()

        def produce(producer_index: int) -> None:
            start = producer_index * items_per_producer
            for item in range(start, start + items_per_producer):
                queue.put(item, timeout=1)

        def consume() -> None:
            while True:
                try:
                    item = queue.get(timeout=1)
                except ShutDown:
                    return
                try:
                    with processed_lock:
                        processed.append(item)
                finally:
                    queue.task_done()

        with ThreadPoolExecutor(max_workers=producer_count + consumer_count) as executor:
            consumer_futures = [
                executor.submit(consume) for _ in range(consumer_count)
            ]
            producer_futures = [
                executor.submit(produce, index) for index in range(producer_count)
            ]

            for future in producer_futures:
                future.result(timeout=1)
            queue.shutdown()
            for future in consumer_futures:
                future.result(timeout=1)

        queue.join()
        self.assertEqual(sorted(processed), list(range(total_items)))
        self.assertEqual(queue.size(), 0)


if __name__ == "__main__":
    unittest.main()
