"""Track request metrics from many concurrent callers.

The business logic is a small metrics collector: callers record started
requests, successful completions, failed completions, and the highest number of
requests that were in flight at the same time.

The example uses `threading.Lock` because the counters form one shared snapshot.
The lock keeps increments, decrements, and peak in-flight updates consistent for
all threads.
"""

from python_concurrency_examples.examples.atomiccounter.metrics import Metrics, Snapshot

__all__ = ["Metrics", "Snapshot"]
