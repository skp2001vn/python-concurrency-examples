"""Keep request IDs isolated per async task.

The business logic is an async request logging workflow: each coroutine needs a
request ID for log messages, audit records, or tracing, and that ID must not
leak into other concurrent request tasks.

The example uses `contextvars.ContextVar` because async tasks often share one
thread. Context variables preserve request-local state across awaits while
keeping sibling task contexts independent.
"""

from contextvars import ContextVar, Token


class AsyncRequestContext:
    """AsyncRequestContext stores request metadata for the current async task.

    The context object can be shared across many async tasks. Setting, reading,
    and resetting the request ID affects the current task context without
    changing sibling task contexts.
    """

    def __init__(self) -> None:
        """Create an empty async request context."""
        self._request_id: ContextVar[str | None] = ContextVar(
            "request_id",
            default=None,
        )

    def set_request_id(self, request_id: str) -> Token[str | None]:
        """Store the current task's request ID and return a reset token."""
        if not request_id:
            raise ValueError("request_id must not be empty")

        return self._request_id.set(request_id)

    def get_request_id(self) -> str | None:
        """Return the current task's request ID, if one is set."""
        return self._request_id.get()

    def reset(self, token: Token[str | None]) -> None:
        """Restore the request ID state captured by token."""
        self._request_id.reset(token)
