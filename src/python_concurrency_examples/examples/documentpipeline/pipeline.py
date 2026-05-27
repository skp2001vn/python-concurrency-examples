"""Move documents through staged processing workers.

The business logic is a document processing workflow: incoming documents pass
through ordered stages such as parse, validate, enrich, and publish before they
are considered complete.

The example uses `queue.Queue` to hand work from one stage to the next and
`threading.Thread` to run each stage worker independently. Shutdown sends a
sentinel through the stages after queued documents so workers drain pending work
before exiting.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from queue import Queue
from threading import Lock, Thread
from time import monotonic
from typing import Any


@dataclass(frozen=True, slots=True)
class DocumentFailure:
    """DocumentFailure reports a document that failed one pipeline stage.

    Attributes:
        document: Original submitted document.
        stage: Name of the stage that failed.
        error: Exception raised by the stage function.
    """

    document: object
    stage: str
    error: Exception


@dataclass(frozen=True, slots=True)
class _PipelineItem:
    original: object
    current: object


class DocumentPipeline:
    """DocumentPipeline processes documents through ordered worker stages.

    The pipeline is safe for submissions from many threads. Each document moves
    through the configured stages in order, successful outputs are recorded, and
    failures stop that document while allowing other documents to continue.
    """

    def __init__(
        self,
        stages: Sequence[tuple[str, Callable[[Any], Any]]],
    ) -> None:
        """Create and start a worker pipeline from ordered named stages."""
        if not stages:
            raise ValueError("stages must not be empty")
        if any(not name for name, _stage in stages):
            raise ValueError("stage names must not be empty")

        self._stages = list(stages)
        self._sentinel = object()
        self._queues: list[Queue[_PipelineItem | object]] = [
            Queue() for _ in self._stages
        ]
        self._lock = Lock()
        self._closed = False
        self._results: list[object] = []
        self._failures: list[DocumentFailure] = []
        self._workers = [
            Thread(
                target=self._run_stage,
                args=(index,),
                name=f"DocumentPipeline-{stage_name}",
                daemon=True,
            )
            for index, (stage_name, _stage) in enumerate(self._stages)
        ]
        for worker in self._workers:
            worker.start()

    def submit(self, document: object) -> None:
        """Submit one document for staged processing."""
        with self._lock:
            if self._closed:
                raise RuntimeError("document pipeline is closed")
            self._queues[0].put(_PipelineItem(original=document, current=document))

    def close(self, timeout: float | None = None) -> bool:
        """Drain queued documents and return whether workers stopped in time."""
        with self._lock:
            if not self._closed:
                self._closed = True
                self._queues[0].put(self._sentinel)

        deadline = None if timeout is None else monotonic() + timeout
        for worker in self._workers:
            join_timeout = None
            if deadline is not None:
                join_timeout = max(0.0, deadline - monotonic())
            worker.join(timeout=join_timeout)

        return all(not worker.is_alive() for worker in self._workers)

    def results(self) -> tuple[object, ...]:
        """Return successful final document outputs."""
        with self._lock:
            return tuple(self._results)

    def failures(self) -> tuple[DocumentFailure, ...]:
        """Return document stage failures captured by workers."""
        with self._lock:
            return tuple(self._failures)

    def _run_stage(self, stage_index: int) -> None:
        stage_name, stage = self._stages[stage_index]
        queue = self._queues[stage_index]
        while True:
            item = queue.get()
            try:
                if item is self._sentinel:
                    self._forward_sentinel(stage_index)
                    return

                if not isinstance(item, _PipelineItem):
                    raise RuntimeError("unexpected pipeline item")
                try:
                    output = stage(item.current)
                except Exception as error:
                    with self._lock:
                        self._failures.append(
                            DocumentFailure(
                                document=item.original,
                                stage=stage_name,
                                error=error,
                            ),
                        )
                    continue

                self._forward_item(stage_index, item.original, output)
            finally:
                queue.task_done()

    def _forward_item(
        self,
        stage_index: int,
        original: object,
        output: object,
    ) -> None:
        if stage_index == len(self._stages) - 1:
            with self._lock:
                self._results.append(output)
            return

        self._queues[stage_index + 1].put(
            _PipelineItem(original=original, current=output),
        )

    def _forward_sentinel(self, stage_index: int) -> None:
        if stage_index < len(self._stages) - 1:
            self._queues[stage_index + 1].put(self._sentinel)
