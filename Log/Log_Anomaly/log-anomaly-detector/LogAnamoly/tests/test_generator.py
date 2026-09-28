import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from log_ingestion.generator import LogGenerator
from log_ingestion.parser import parse_log_line


class LogGeneratorTests(unittest.TestCase):
    def events_for(self, scenario: str, count: int = 100):
        generator = LogGenerator(scenario=scenario, seed=17)
        timestamp = datetime(2026, 9, 28, tzinfo=timezone.utc)
        events = [parse_log_line(generator.generate_line(timestamp)) for _ in range(count)]
        self.assertTrue(all(event is not None for event in events))
        return events

    def test_normal_scenario_is_mostly_successful(self) -> None:
        events = self.events_for("normal")
        self.assertGreaterEqual(sum(event.status_code < 400 for event in events), 90)
        self.assertLessEqual(sum(event.status_code >= 500 for event in events), 5)

    def test_error_spike_has_high_error_rate(self) -> None:
        events = self.events_for("error_spike")
        self.assertGreater(sum(event.status_code >= 400 for event in events) / len(events), 0.7)

    def test_latency_spike_keeps_latency_high(self) -> None:
        events = self.events_for("latency_spike")
        self.assertGreater(min(event.latency_ms for event in events), 1000)
        self.assertLess(sum(event.status_code >= 500 for event in events), len(events) / 10)

    def test_database_failure_emits_database_messages_and_server_errors(self) -> None:
        events = self.events_for("database_failure")
        self.assertGreater(sum(event.status_code >= 500 for event in events) / len(events), 0.8)
        self.assertTrue(any(event.message.startswith("Database ") for event in events))

    def test_scenario_can_change_and_traffic_spike_scales_rate(self) -> None:
        generator = LogGenerator(rate=10, seed=1)
        normal_interval = generator.interval_for_scenario("normal")
        traffic_interval = generator.interval_for_scenario("traffic_spike")
        self.assertEqual(normal_interval, 0.1)
        self.assertEqual(traffic_interval, 0.02)

        generator.set_scenario("database_failure")
        event = parse_log_line(generator.generate_line())
        self.assertEqual(generator.scenario, "database_failure")
        self.assertIsNotNone(event)
        assert event is not None
        self.assertGreaterEqual(event.status_code, 500)

    def test_background_generator_appends_without_replacing_existing_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "app.log"
            path.write_text("existing\n", encoding="utf-8")
            generator = LogGenerator(path=path, rate=200)
            generator.start()
            generator.stop()
            contents = path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(contents[0], "existing")
            self.assertGreaterEqual(len(contents), 2)


if __name__ == "__main__":
    unittest.main()