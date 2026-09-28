import unittest
from datetime import datetime, timezone

from log_ingestion.parser import parse_log_line


class ParseLogLineTests(unittest.TestCase):
    def test_parses_valid_log(self) -> None:
        event = parse_log_line(
            '2026-09-28T14:10:01+00:00 INFO 200 120.5 api "Request completed"'
        )
        self.assertIsNotNone(event)
        assert event is not None
        self.assertEqual(event.timestamp, datetime(2026, 9, 28, 14, 10, 1, tzinfo=timezone.utc))
        self.assertEqual((event.level, event.status_code, event.latency_ms), ("INFO", 200, 120.5))
        self.assertEqual((event.service, event.message), ("api", "Request completed"))

    def test_invalid_timestamp_is_skipped(self) -> None:
        self.assertIsNone(parse_log_line('not-a-date INFO 200 12 api "Request completed"'))

    def test_invalid_status_code_is_skipped(self) -> None:
        self.assertIsNone(parse_log_line('2026-09-28T14:10:01 INFO nope 12 api "Request completed"'))
        self.assertIsNone(parse_log_line('2026-09-28T14:10:01 INFO 700 12 api "Request completed"'))

    def test_invalid_latency_is_skipped_without_defaulting_to_zero(self) -> None:
        for latency in ("missing", "nan", "inf", "-0.1"):
            with self.subTest(latency=latency):
                self.assertIsNone(
                    parse_log_line(f'2026-09-28T14:10:01 INFO 200 {latency} api "Request completed"')
                )

    def test_malformed_line_is_skipped(self) -> None:
        self.assertIsNone(parse_log_line("not a structured log line"))

    def test_escaped_message_is_preserved(self) -> None:
        event = parse_log_line(r'2026-09-28T14:10:01 INFO 200 12 api "message with \"quotes\""')
        self.assertIsNotNone(event)
        assert event is not None
        self.assertEqual(event.message, 'message with "quotes"')


if __name__ == "__main__":
    unittest.main()