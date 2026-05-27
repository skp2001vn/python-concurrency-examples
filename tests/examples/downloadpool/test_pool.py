"""Unit tests for the downloadpool example.

The example models a reporting job that fetches partner files without allowing
too many downloads to run at once. The tests verify caller-facing behavior:
capacity limits are validated, task results and failures are preserved, timeout
behavior is explicit, and concurrent workers do not exceed the configured cap.
"""

import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event, Lock

from python_concurrency_examples.examples.downloadpool import DownloadPool


class DownloadPoolTest(unittest.TestCase):
    """DownloadPoolTest verifies the public download limiting behavior."""

    # Verifies that callers must choose a positive concurrency limit.
    def test_rejects_invalid_concurrency_limit(self) -> None:
        with self.assertRaises(ValueError):
            DownloadPool(0)

    # Verifies that each download needs a non-empty business identifier.
    def test_rejects_blank_download_id(self) -> None:
        pool = DownloadPool(max_concurrent=1)

        with self.assertRaises(ValueError):
            pool.run("", lambda: "ignored")

    # Verifies that callers receive the completed download result.
    def test_returns_download_result(self) -> None:
        pool = DownloadPool(max_concurrent=1)

        result = pool.run("report.csv", lambda: b"contents")

        self.assertEqual(result, b"contents")

    # Verifies that a failed download releases capacity for later work.
    def test_releases_slot_when_download_fails(self) -> None:
        pool = DownloadPool(max_concurrent=1)

        with self.assertRaises(RuntimeError):
            pool.run("broken.csv", self.raise_download_error)

        self.assertEqual(pool.run("next.csv", lambda: "done"), "done")

    # Verifies that callers can time out while all download slots are busy.
    def test_times_out_when_capacity_is_unavailable(self) -> None:
        pool = DownloadPool(max_concurrent=1)
        download_started = Event()
        release_download = Event()

        def blocking_download() -> str:
            download_started.set()
            if not release_download.wait(timeout=1):
                raise AssertionError("timed out waiting to release download")
            return "finished"

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(pool.run, "first.csv", blocking_download)
            self.assertTrue(download_started.wait(timeout=1))

            with self.assertRaises(TimeoutError):
                pool.run("second.csv", lambda: "blocked", timeout=0)

            release_download.set()
            self.assertEqual(future.result(timeout=1), "finished")

    # Verifies that concurrent workers never exceed the download slot limit.
    def test_limits_concurrent_downloads(self) -> None:
        max_concurrent = 3
        download_count = 12
        pool = DownloadPool(max_concurrent=max_concurrent)
        ready = Barrier(download_count + 1)
        first_wave_ready = Event()
        release_downloads = Event()
        active_lock = Lock()
        active_count = 0
        entered_count = 0
        peak_active_count = 0

        def tracked_download() -> bool:
            nonlocal active_count, entered_count, peak_active_count
            with active_lock:
                active_count += 1
                entered_count += 1
                peak_active_count = max(peak_active_count, active_count)
                if entered_count == max_concurrent:
                    first_wave_ready.set()

            try:
                if not release_downloads.wait(timeout=1):
                    raise AssertionError("timed out waiting to release downloads")
                return True
            finally:
                with active_lock:
                    active_count -= 1

        def worker(index: int) -> bool:
            ready.wait(timeout=1)
            return pool.run(f"file-{index}.csv", tracked_download)

        with ThreadPoolExecutor(max_workers=download_count) as executor:
            futures = [executor.submit(worker, index) for index in range(download_count)]
            ready.wait(timeout=1)
            if not first_wave_ready.wait(timeout=1):
                release_downloads.set()
                self.fail("timed out waiting for first download wave")

            with active_lock:
                self.assertEqual(active_count, max_concurrent)
                self.assertEqual(peak_active_count, max_concurrent)

            release_downloads.set()
            self.assertEqual(
                [future.result(timeout=1) for future in futures],
                [True] * download_count,
            )

        self.assertEqual(peak_active_count, max_concurrent)

    def raise_download_error(self) -> None:
        """Raise a fixed error from a simulated download."""
        raise RuntimeError("download failed")


if __name__ == "__main__":
    unittest.main()
