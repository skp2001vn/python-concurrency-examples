"""Route customer support tickets by priority.

Use `queue.PriorityQueue` for thread-safe prioritized handoff to agent workers.
"""

from concurrencyexamples.supportqueue.queue import (
    SupportQueue,
    SupportTicket,
)

__all__ = ["SupportQueue", "SupportTicket"]
