import unittest
from datetime import datetime, timedelta

from log_ingestion.models import LogEvent
from log_ingestion.window import SlidingWindow
from helpers import make_window


class SlidingWindowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.base = datetime(2026, 9, 28, 14, 10, 0)

    def event(self, seconds: float, status: int = 200, latency: float = 100.0) -> LogEvent:
        return LogEvent(self.base + timedelta(seconds=seconds), "INFO", status, latency, "api", "test")

    def manager(self) -> SlidingWindow:
        return SlidingWindow(window_factory=make_window)

    def test_counts_errors_server_errors_and_average_latency(self) -> None:
        window_manager = self.manager()
        window_manager.add(self.event(1, 200, 100.0))
        window_manager.add(self.event(9, 404, 200.0))
        window_manager.add(self.event(59, 503, 300.0))
        windows = window_manager.add(self.event(60, 201, 10000.0))

        base_window = next(window for window in windows if window.window_start == self.base)
        self.assertEqual(base_window.total_requests, 3)
        self.assertEqual(base_window.error_count, 2)
        self.assertEqual(base_window.server_error_count, 1)
        self.assertAlmostEqual(base_window.avg_latency_ms, 200.0)

    def test_slides_every_ten_seconds_using_event_time(self) -> None:
        window_manager = self.manager()
        window_manager.add(self.event(1))
        windows = window_manager.advance_watermark(self.base + timedelta(seconds=60))
        starts = sorted(window.window_start for window in windows)
        self.assertEqual(len(windows), 6)
        self.assertEqual(
            [int((self.base - start).total_seconds()) for start in starts],
            [50, 40, 30, 20, 10, 0],
        )
        self.assertTrue(all(window.total_requests == 1 for window in windows))

    def test_events_outside_active_windows_are_removed(self) -> None:
        window_manager = self.manager()
        window_manager.add(self.event(1))
        window_manager.add(self.event(61))
        window_manager.advance_watermark(self.base + timedelta(seconds=120))
        self.assertTrue(all(bucket >= 7 for bucket in window_manager._buckets))

    def test_empty_windows_are_skipped_and_late_events_are_not_reemitted(self) -> None:
        window_manager = self.manager()
        self.assertEqual(window_manager.advance_watermark(self.base + timedelta(seconds=120)), [])
        self.assertEqual(window_manager.add(self.event(1)), [])

    def test_rejects_incompatible_window_configuration(self) -> None:
        with self.assertRaises(ValueError):
            SlidingWindow(duration_seconds=61, slide_seconds=10, window_factory=make_window)


if __name__ == "__main__":
    unittest.main()