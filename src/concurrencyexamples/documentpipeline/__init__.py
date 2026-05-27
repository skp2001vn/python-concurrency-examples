"""Move documents through staged processing workers.

Use `queue.Queue` and `threading.Thread` to pass documents through ordered
pipeline stages and drain work during shutdown.
"""

from concurrencyexamples.documentpipeline.pipeline import (
    DocumentFailure,
    DocumentPipeline,
)

__all__ = ["DocumentFailure", "DocumentPipeline"]
