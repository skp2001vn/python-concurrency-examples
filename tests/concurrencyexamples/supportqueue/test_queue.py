"""Unit tests for the supportqueue example.

The example models customer support tickets submitted by producer threads and
claimed by agent threads. The tests verify caller-facing behavior: invalid
tickets are rejected, urgent tickets are claimed first, same-priority tickets
keep submission order, empty queues return `None`, and concurrent agents claim
each ticket at most once.
"""

import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

from concurrencyexamples.supportqueue import (
    SupportQueue,
    SupportTicket,
)


class SupportQueueTest(unittest.TestCase):
    """SupportQueueTest verifies the public priority queue behavior."""

    # Verifies that ticket IDs must be non-empty.
    def test_rejects_empty_ticket_id(self) -> None:
        with self.assertRaises(ValueError):
            SupportTicket(
                ticket_id="",
                customer_id="customer-1",
                priority=1,
                subject="Cannot sign in",
            )

    # Verifies that customer IDs must be non-empty.
    def test_rejects_empty_customer_id(self) -> None:
        with self.assertRaises(ValueError):
            SupportTicket(
                ticket_id="ticket-1",
                customer_id="",
                priority=1,
                subject="Cannot sign in",
            )

    # Verifies that priority values cannot be negative.
    def test_rejects_negative_priority(self) -> None:
        with self.assertRaises(ValueError):
            SupportTicket(
                ticket_id="ticket-1",
                customer_id="customer-1",
                priority=-1,
                subject="Cannot sign in",
            )

    # Verifies that subjects must be non-empty.
    def test_rejects_empty_subject(self) -> None:
        with self.assertRaises(ValueError):
            SupportTicket(
                ticket_id="ticket-1",
                customer_id="customer-1",
                priority=1,
                subject="",
            )

    # Verifies that agent workers receive urgent tickets before normal tickets.
    def test_claims_lower_priority_number_first(self) -> None:
        queue = SupportQueue()
        normal_ticket = self.ticket("normal", priority=5)
        urgent_ticket = self.ticket("urgent", priority=0)

        queue.submit(normal_ticket)
        queue.submit(urgent_ticket)

        self.assertEqual(queue.claim_next(), urgent_ticket)
        queue.task_done()
        self.assertEqual(queue.claim_next(), normal_ticket)
        queue.task_done()
        queue.join()

    # Verifies that same-priority tickets keep submission order.
    def test_claims_same_priority_tickets_in_submission_order(self) -> None:
        queue = SupportQueue()
        first_ticket = self.ticket("first", priority=3)
        second_ticket = self.ticket("second", priority=3)

        queue.submit(first_ticket)
        queue.submit(second_ticket)

        self.assertEqual(queue.claim_next(), first_ticket)
        queue.task_done()
        self.assertEqual(queue.claim_next(), second_ticket)
        queue.task_done()
        queue.join()

    # Verifies that empty queues return None instead of blocking forever.
    def test_claim_next_returns_none_when_empty(self) -> None:
        queue = SupportQueue()

        self.assertIsNone(queue.claim_next())

    # Verifies that producer threads can submit all tickets safely.
    def test_concurrent_producers_submit_all_tickets(self) -> None:
        ticket_count = 50
        queue = SupportQueue()

        def submit_ticket(index: int) -> None:
            queue.submit(self.ticket(f"ticket-{index}", priority=index % 5))

        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [
                executor.submit(submit_ticket, index)
                for index in range(ticket_count)
            ]
            for future in futures:
                future.result(timeout=1)

        claimed_ticket_ids = set()
        while ticket := queue.claim_next():
            claimed_ticket_ids.add(ticket.ticket_id)
            queue.task_done()

        queue.join()
        self.assertEqual(
            claimed_ticket_ids,
            {f"ticket-{index}" for index in range(ticket_count)},
        )
        self.assertEqual(queue.size(), 0)

    # Verifies that concurrent agents claim each waiting ticket at most once.
    def test_concurrent_agents_claim_each_ticket_once(self) -> None:
        ticket_count = 80
        agent_count = 6
        queue = SupportQueue()
        claimed_ticket_ids: list[str] = []
        claimed_lock = Lock()

        for index in range(ticket_count):
            queue.submit(self.ticket(f"ticket-{index}", priority=index % 4))

        def claim_tickets() -> None:
            while ticket := queue.claim_next():
                try:
                    with claimed_lock:
                        claimed_ticket_ids.append(ticket.ticket_id)
                finally:
                    queue.task_done()

        with ThreadPoolExecutor(max_workers=agent_count) as executor:
            futures = [executor.submit(claim_tickets) for _ in range(agent_count)]
            for future in futures:
                future.result(timeout=1)

        queue.join()
        self.assertEqual(len(claimed_ticket_ids), ticket_count)
        self.assertEqual(
            set(claimed_ticket_ids),
            {f"ticket-{index}" for index in range(ticket_count)},
        )
        self.assertEqual(len(set(claimed_ticket_ids)), ticket_count)

    def ticket(self, ticket_id: str, priority: int) -> SupportTicket:
        """Create one valid support ticket for tests."""
        return SupportTicket(
            ticket_id=ticket_id,
            customer_id=f"customer-{ticket_id}",
            priority=priority,
            subject=f"Subject for {ticket_id}",
        )


if __name__ == "__main__":
    unittest.main()
