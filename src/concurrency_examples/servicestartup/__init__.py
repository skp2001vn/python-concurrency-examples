"""Wait for startup work before accepting service requests.

Use `threading.Event` to broadcast readiness to request handlers once startup
tasks finish.
"""

from concurrency_examples.servicestartup.startup import ServiceStartup

__all__ = ["ServiceStartup"]
