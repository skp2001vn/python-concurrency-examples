"""Keep request IDs isolated per request thread.

The business logic is a request logging workflow: each worker thread needs a
request ID for log messages, audit records, or tracing, and that ID must not
leak into other request threads.

The example uses `threading.local` because request context is owned by the
current thread. Each thread sees its own request ID even when all threads share
the same `RequestContext` instance.
"""

from threading import local


class RequestContext:
    """RequestContext stores request metadata for the current thread.

    The context object can be shared across many threads. Setting, reading, and
    clearing the request ID affects only the calling thread's context.
    """

    def __init__(self) -> None:
        """Create an empty per-thread request context."""
        self._local = local()

    def set_request_id(self, request_id: str) -> None:
        """Store the current thread's request ID."""
        if not request_id:
            raise ValueError("request_id must not be empty")

        self._local.request_id = request_id

    def get_request_id(self) -> str | None:
        """Return the current thread's request ID, if one is set."""
        return getattr(self._local, "request_id", None)

    def clear(self) -> None:
        """Remove the current thread's request ID if one is set."""
        if hasattr(self._local, "request_id"):
            del self._local.request_id
