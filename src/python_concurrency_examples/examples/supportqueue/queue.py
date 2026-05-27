"""Route customer support tickets by priority.

The business logic is a support desk workflow: tickets arrive from email,
chat, and phone, while several agent threads claim the next ticket to handle.
Urgent tickets should be handled before normal tickets.

The example uses `queue.PriorityQueue` because it owns the locking and
condition signaling needed for safe prioritized handoff between producer and
agent threads. Lower priority numbers are claimed first, and a sequence number
keeps same-priority tickets in submission order.
"""

from dataclasses import dataclass
from queue import Empty, PriorityQueue
from threading import Lock


@dataclass(frozen=True, slots=True)
class SupportTicket:
    """SupportTicket describes one customer issue waiting for an agent.

    Attributes:
        ticket_id: Stable identifier for the support ticket.
        customer_id: Stable identifier for the customer.
        priority: Routing priority where lower numbers are more urgent.
        subject: Short caller-facing ticket summary.
    """

    ticket_id: str
    customer_id: str
    priority: int
    subject: str

    def __post_init__(self) -> None:
        """Validate ticket fields required for priority routing."""
        if not self.ticket_id:
            raise ValueError("ticket_id must not be empty")
        if not self.customer_id:
            raise ValueError("customer_id must not be empty")
        if self.priority < 0:
            raise ValueError("priority must not be negative")
        if not self.subject:
            raise ValueError("subject must not be empty")


class SupportQueue:
    """SupportQueue lets producer threads submit tickets for agent workers.

    The queue is safe for concurrent use by many threads. Producers submit
    tickets, agent workers claim the most urgent pending ticket, and callers
    receive `None` when no ticket is currently waiting.
    """

    def __init__(self) -> None:
        """Create an empty support queue."""
        self._queue: PriorityQueue[tuple[int, int, SupportTicket]] = PriorityQueue()
        self._sequence_lock = Lock()
        self._next_sequence = 0

    def submit(self, ticket: SupportTicket) -> None:
        """Submit one ticket for prioritized agent handling."""
        with self._sequence_lock:
            sequence = self._next_sequence
            self._next_sequence += 1

        self._queue.put((ticket.priority, sequence, ticket))

    def claim_next(self) -> SupportTicket | None:
        """Claim the next ticket, or return `None` when the queue is empty."""
        try:
            _, _, ticket = self._queue.get(block=False)
        except Empty:
            return None
        return ticket

    def task_done(self) -> None:
        """Mark one previously claimed ticket as handled."""
        self._queue.task_done()

    def join(self) -> None:
        """Block until all claimed tickets have been marked as handled."""
        self._queue.join()

    def size(self) -> int:
        """Return the approximate number of waiting tickets."""
        return self._queue.qsize()
