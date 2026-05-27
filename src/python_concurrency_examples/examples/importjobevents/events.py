"""Collect import job events from worker processes.

The business logic is a data-import workflow: separate worker processes import
large customer CSV files and send progress events back to the parent process.

The example uses `multiprocessing.Queue` because child processes do not share
memory with the parent process. Events must be picklable messages, and each
worker sends a sentinel when it finishes so the parent collector knows when all
processes have stopped producing events.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from multiprocessing import Process, Queue
from typing import Literal

ImportJobStage = Literal["started", "parsed", "validated", "stored", "failed"]

_VALID_STAGES = frozenset(
    {"started", "parsed", "validated", "stored", "failed"}
)


@dataclass(frozen=True, slots=True)
class ImportJob:
    """ImportJob describes one customer file import handled by a process.

    Attributes:
        job_id: Stable identifier for the import job.
        file_name: Name of the file being imported.
        row_count: Number of rows expected in the file.
        should_fail_validation: Whether the worker should emit a failed event.
    """

    job_id: str
    file_name: str
    row_count: int
    should_fail_validation: bool = False

    def __post_init__(self) -> None:
        """Validate import job fields before starting worker processes."""
        if not self.job_id:
            raise ValueError("job_id must not be empty")
        if not self.file_name:
            raise ValueError("file_name must not be empty")
        if self.row_count < 0:
            raise ValueError("row_count must not be negative")


@dataclass(frozen=True, slots=True)
class ImportJobEvent:
    """ImportJobEvent reports one progress update from an import worker.

    Attributes:
        job_id: Stable identifier for the import job.
        stage: Import progress stage.
        detail: Caller-facing detail about the progress update.
    """

    job_id: str
    stage: ImportJobStage
    detail: str

    def __post_init__(self) -> None:
        """Validate event fields before they cross process boundaries."""
        if not self.job_id:
            raise ValueError("job_id must not be empty")
        if self.stage not in _VALID_STAGES:
            raise ValueError("stage must be a known import stage")
        if not self.detail:
            raise ValueError("detail must not be empty")


@dataclass(frozen=True, slots=True)
class _WorkerFinished:
    job_id: str


class ImportJobEventCollector:
    """ImportJobEventCollector gathers progress events from child processes.

    The collector starts one process per import job and receives picklable event
    messages through a process-safe queue. Events from different workers may
    arrive in any order, so callers should not rely on global ordering.
    """

    def collect(self, jobs: Iterable[ImportJob]) -> tuple[ImportJobEvent, ...]:
        """Run import workers and return all collected progress events."""
        job_batch = tuple(jobs)
        if not job_batch:
            raise ValueError("jobs must not be empty")

        events = Queue()
        processes = [
            Process(
                target=_run_import_job,
                args=(job, events),
                name=f"ImportJob-{job.job_id}",
            )
            for job in job_batch
        ]

        for process in processes:
            process.start()

        collected_events: list[ImportJobEvent] = []
        finished_workers = 0
        while finished_workers < len(processes):
            message = events.get()
            if isinstance(message, _WorkerFinished):
                finished_workers += 1
            else:
                collected_events.append(message)

        for process in processes:
            process.join()
            if process.exitcode != 0:
                raise RuntimeError(f"{process.name} exited with {process.exitcode}")

        events.close()
        events.join_thread()
        return tuple(collected_events)


def _run_import_job(job: ImportJob, events) -> None:
    try:
        events.put(
            ImportJobEvent(
                job_id=job.job_id,
                stage="started",
                detail=f"started importing {job.file_name}",
            )
        )
        events.put(
            ImportJobEvent(
                job_id=job.job_id,
                stage="parsed",
                detail=f"parsed {job.row_count} rows",
            )
        )
        if job.should_fail_validation:
            raise ValueError(f"{job.file_name} failed validation")

        events.put(
            ImportJobEvent(
                job_id=job.job_id,
                stage="validated",
                detail="validated rows",
            )
        )
        events.put(
            ImportJobEvent(
                job_id=job.job_id,
                stage="stored",
                detail="stored import rows",
            )
        )
    except Exception as error:
        events.put(
            ImportJobEvent(
                job_id=job.job_id,
                stage="failed",
                detail=str(error),
            )
        )
    finally:
        events.put(_WorkerFinished(job_id=job.job_id))
