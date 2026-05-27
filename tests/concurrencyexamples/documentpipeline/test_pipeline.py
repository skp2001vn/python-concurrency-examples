"""Unit tests for the documentpipeline example.

The example models documents moving through parse, validate, enrich, and publish
workers. The tests verify caller-facing behavior: invalid stages are rejected,
documents pass through stages in order, failures are captured, multiple
documents drain on close, and submissions after close are rejected.
"""

import unittest
from concurrent.futures import ThreadPoolExecutor

from concurrencyexamples.documentpipeline import (
    DocumentFailure,
    DocumentPipeline,
)


class DocumentPipelineTest(unittest.TestCase):
    """DocumentPipelineTest verifies the public staged processing behavior."""

    # Verifies that callers must configure at least one named stage.
    def test_rejects_invalid_stages(self) -> None:
        with self.assertRaises(ValueError):
            DocumentPipeline([])
        with self.assertRaises(ValueError):
            DocumentPipeline([("", lambda document: document)])

    # Verifies that one document passes through every stage in order.
    def test_processes_document_through_ordered_stages(self) -> None:
        pipeline = DocumentPipeline(
            [
                ("parse", lambda document: f"parsed:{document}"),
                ("validate", lambda document: f"valid:{document}"),
                ("publish", lambda document: f"published:{document}"),
            ],
        )

        pipeline.submit("doc-1")
        self.assertTrue(pipeline.close(timeout=1))

        self.assertEqual(
            pipeline.results(),
            ("published:valid:parsed:doc-1",),
        )
        self.assertEqual(pipeline.failures(), ())

    # Verifies that multiple documents are drained before close returns.
    def test_close_drains_multiple_documents(self) -> None:
        pipeline = DocumentPipeline(
            [
                ("parse", lambda document: document.upper()),
                ("publish", lambda document: f"published:{document}"),
            ],
        )

        for document in ["doc-a", "doc-b", "doc-c"]:
            pipeline.submit(document)
        self.assertTrue(pipeline.close(timeout=1))

        self.assertEqual(
            set(pipeline.results()),
            {
                "published:DOC-A",
                "published:DOC-B",
                "published:DOC-C",
            },
        )

    # Verifies that stage failures are captured without stopping other documents.
    def test_captures_stage_failure(self) -> None:
        def validate(document: str) -> str:
            if document == "bad":
                raise RuntimeError("invalid document")
            return document

        pipeline = DocumentPipeline(
            [
                ("validate", validate),
                ("publish", lambda document: f"published:{document}"),
            ],
        )

        pipeline.submit("good")
        pipeline.submit("bad")
        self.assertTrue(pipeline.close(timeout=1))

        self.assertEqual(pipeline.results(), ("published:good",))
        failures = pipeline.failures()
        self.assertEqual(len(failures), 1)
        self.assertEqual(
            failures[0],
            DocumentFailure(
                document="bad",
                stage="validate",
                error=failures[0].error,
            ),
        )
        self.assertIsInstance(failures[0].error, RuntimeError)

    # Verifies that submissions after close are rejected.
    def test_rejects_submit_after_close(self) -> None:
        pipeline = DocumentPipeline([("publish", lambda document: document)])

        self.assertTrue(pipeline.close(timeout=1))

        with self.assertRaises(RuntimeError):
            pipeline.submit("doc-1")

    # Verifies that many producer threads can submit documents safely.
    def test_accepts_concurrent_submissions(self) -> None:
        document_count = 25
        pipeline = DocumentPipeline(
            [
                ("parse", lambda document: f"parsed:{document}"),
                ("publish", lambda document: f"published:{document}"),
            ],
        )

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(pipeline.submit, f"doc-{index}")
                for index in range(document_count)
            ]
            for future in futures:
                future.result(timeout=1)
        self.assertTrue(pipeline.close(timeout=1))

        self.assertEqual(
            set(pipeline.results()),
            {
                f"published:parsed:doc-{index}"
                for index in range(document_count)
            },
        )


if __name__ == "__main__":
    unittest.main()
