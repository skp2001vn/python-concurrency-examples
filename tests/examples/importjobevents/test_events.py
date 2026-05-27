"""Unit tests for the importjobevents example.

The example models customer import jobs running in child processes and sending
progress events to the parent process. The tests verify caller-facing behavior:
invalid messages are rejected, process events are collected, failed imports
emit failure events, and multiple workers report all events before sentinel
shutdown completes.
"""

import unittest

from python_concurrency_examples.examples.importjobevents import (
    ImportJob,
    ImportJobEvent,
    ImportJobEventCollector,
)


class ImportJobEventCollectorTest(unittest.TestCase):
    """ImportJobEventCollectorTest verifies cross-process event collection."""

    # Verifies that import job IDs must be non-empty.
    def test_rejects_empty_job_id(self) -> None:
        with self.assertRaises(ValueError):
            ImportJob(job_id="", file_name="customers.csv", row_count=10)

    # Verifies that import file names must be non-empty.
    def test_rejects_empty_file_name(self) -> None:
        with self.assertRaises(ValueError):
            ImportJob(job_id="job-1", file_name="", row_count=10)

    # Verifies that row counts cannot be negative.
    def test_rejects_negative_row_count(self) -> None:
        with self.assertRaises(ValueError):
            ImportJob(job_id="job-1", file_name="customers.csv", row_count=-1)

    # Verifies that progress events must use a known stage.
    def test_rejects_unknown_event_stage(self) -> None:
        with self.assertRaises(ValueError):
            ImportJobEvent(job_id="job-1", stage="unknown", detail="bad stage")

    # Verifies that callers must provide at least one import job.
    def test_rejects_empty_job_batch(self) -> None:
        collector = ImportJobEventCollector()

        with self.assertRaises(ValueError):
            collector.collect([])

    # Verifies that one successful import reports its expected progress stages.
    def test_collects_events_for_successful_import(self) -> None:
        collector = ImportJobEventCollector()
        job = ImportJob(job_id="job-1", file_name="customers.csv", row_count=25)

        events = collector.collect([job])

        self.assertEqual(
            [event.stage for event in events],
            ["started", "parsed", "validated", "stored"],
        )
        self.assertEqual({event.job_id for event in events}, {"job-1"})

    # Verifies that a failed import reports failure instead of stored.
    def test_collects_failure_event_for_failed_import(self) -> None:
        collector = ImportJobEventCollector()
        job = ImportJob(
            job_id="job-1",
            file_name="customers.csv",
            row_count=25,
            should_fail_validation=True,
        )

        events = collector.collect([job])

        self.assertEqual(
            [event.stage for event in events],
            ["started", "parsed", "failed"],
        )
        self.assertIn("failed validation", events[-1].detail)

    # Verifies that multiple worker processes send all events before shutdown.
    def test_collects_events_from_multiple_workers(self) -> None:
        collector = ImportJobEventCollector()
        jobs = [
            ImportJob(job_id="job-1", file_name="customers.csv", row_count=25),
            ImportJob(job_id="job-2", file_name="orders.csv", row_count=40),
            ImportJob(
                job_id="job-3",
                file_name="bad.csv",
                row_count=5,
                should_fail_validation=True,
            ),
        ]

        events = collector.collect(jobs)
        stages_by_job = {
            job_id: {event.stage for event in events if event.job_id == job_id}
            for job_id in {job.job_id for job in jobs}
        }

        self.assertEqual(
            stages_by_job,
            {
                "job-1": {"started", "parsed", "validated", "stored"},
                "job-2": {"started", "parsed", "validated", "stored"},
                "job-3": {"started", "parsed", "failed"},
            },
        )
        self.assertEqual(len(events), 11)


if __name__ == "__main__":
    unittest.main()
