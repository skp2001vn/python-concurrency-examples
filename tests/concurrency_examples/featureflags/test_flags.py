"""Unit tests for the featureflags example.

The example models an in-memory service configuration snapshot. The tests
verify caller-facing behavior: invalid flag names are rejected, missing flags
default to disabled, refreshes replace the snapshot atomically, nested reads do
not deadlock, and concurrent readers only observe valid snapshots.
"""

import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from concurrency_examples.featureflags import FeatureFlags


class FeatureFlagsTest(unittest.TestCase):
    """FeatureFlagsTest verifies the public feature flag behavior."""

    # Verifies that flag names must be non-empty.
    def test_rejects_blank_flag_names(self) -> None:
        with self.assertRaises(ValueError):
            FeatureFlags({"": True})

        flags = FeatureFlags({"checkout": True})
        with self.assertRaises(ValueError):
            flags.is_enabled("")
        with self.assertRaises(ValueError):
            flags.replace_all({"": False})

    # Verifies that missing flags default to disabled.
    def test_missing_flags_default_to_disabled(self) -> None:
        flags = FeatureFlags({"checkout": True})

        self.assertFalse(flags.is_enabled("search"))

    # Verifies that callers can read enabled and disabled flag values.
    def test_reads_existing_flag_values(self) -> None:
        flags = FeatureFlags({"checkout": True, "search": False})

        self.assertTrue(flags.is_enabled("checkout"))
        self.assertFalse(flags.is_enabled("search"))

    # Verifies that refresh replaces the whole snapshot atomically.
    def test_replaces_full_snapshot(self) -> None:
        flags = FeatureFlags({"checkout": True, "search": False})

        flags.replace_all({"search": True})

        self.assertFalse(flags.is_enabled("checkout"))
        self.assertTrue(flags.is_enabled("search"))
        self.assertEqual(flags.snapshot(), {"search": True})

    # Verifies that nested lock-protected reads do not deadlock.
    def test_returns_enabled_flags_through_nested_reads(self) -> None:
        flags = FeatureFlags(
            {
                "checkout": True,
                "search": False,
                "recommendations": True,
            },
        )

        self.assertEqual(
            flags.enabled_flags(),
            frozenset({"checkout", "recommendations"}),
        )

    # Verifies that concurrent readers only observe complete refreshed snapshots.
    def test_concurrent_readers_see_valid_snapshots(self) -> None:
        flags = FeatureFlags({"checkout": True, "search": False})
        snapshots = [
            {"checkout": True, "search": False},
            {"checkout": False, "search": True},
        ]
        reader_count = 8
        refresh_count = 50
        ready = Barrier(reader_count + 2)

        def read_flags() -> list[dict[str, bool]]:
            observed: list[dict[str, bool]] = []
            ready.wait(timeout=1)
            for _ in range(refresh_count):
                observed.append(flags.snapshot())
            return observed

        def refresh_flags() -> None:
            ready.wait(timeout=1)
            for index in range(refresh_count):
                flags.replace_all(snapshots[index % len(snapshots)])

        with ThreadPoolExecutor(max_workers=reader_count + 1) as executor:
            reader_futures = [
                executor.submit(read_flags)
                for _ in range(reader_count)
            ]
            refresh_future = executor.submit(refresh_flags)
            ready.wait(timeout=1)
            refresh_future.result(timeout=1)
            observed = [
                snapshot
                for future in reader_futures
                for snapshot in future.result(timeout=1)
            ]

        self.assertTrue(observed)
        self.assertTrue(all(snapshot in snapshots for snapshot in observed))


if __name__ == "__main__":
    unittest.main()
