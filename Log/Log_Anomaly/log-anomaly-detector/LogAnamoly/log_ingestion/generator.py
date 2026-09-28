"""Scenario-driven synthetic HTTP request log generator."""

import argparse
import json
import random
import threading
from datetime import datetime, timezone
from pathlib import Path

from log_ingestion.config import PROFILES, SCENARIOS, Scenario


class LogGenerator:
    """Append deterministic scenario logs to a growing file."""

    def __init__(
        self,
        path: str | Path = "app.log",
        rate: float = 1.0,
        scenario: Scenario = "normal",
        seed: int = 0,
    ) -> None:
        if rate <= 0:
            raise ValueError("rate must be positive")
        if scenario not in PROFILES:
            raise ValueError(f"unknown scenario: {scenario}")
        self.path = Path(path)
        self.rate = rate
        self._scenario = scenario
        self._rng = random.Random(seed)
        self._sequence_index = 0
        self._condition = threading.Condition()
        self._scenario_version = 0
        self._stopping = False
        self._thread: threading.Thread | None = None

    @property
    def scenario(self) -> Scenario:
        with self._condition:
            return self._scenario

    def set_scenario(self, scenario: Scenario) -> None:
        """Switch scenarios safely while the generator is running."""
        if scenario not in PROFILES:
            raise ValueError(f"unknown scenario: {scenario}")
        with self._condition:
            self._scenario = scenario
            self._sequence_index = 0
            self._scenario_version += 1
            self._condition.notify_all()

    def interval_for_scenario(self, scenario: Scenario | None = None) -> float:
        """Return the target interval between events for a scenario."""
        selected = scenario or self.scenario
        return 1.0 / (self.rate * PROFILES[selected].traffic_multiplier)

    def generate_line(self, timestamp: datetime | None = None) -> str:
        """Generate one reproducible-format request line without writing it."""
        timestamp = timestamp or datetime.now(timezone.utc)
        with self._condition:
            scenario = self._scenario
            profile = PROFILES[scenario]
            index = self._sequence_index
            self._sequence_index += 1
            status_code = profile.statuses[index % len(profile.statuses)]
            latency_ms = self._rng.uniform(profile.latency_min_ms, profile.latency_max_ms)

            if scenario == "database_failure" and status_code >= 500:
                message = profile.database_messages[index % len(profile.database_messages)]
            elif status_code >= 500:
                message = "Upstream service error"
            elif status_code >= 400:
                message = "Resource not found"
            else:
                message = "Request completed"

        return (
            f"{timestamp.isoformat(timespec='milliseconds')} "
            f"{'ERROR' if status_code >= 500 else 'INFO'} {status_code} "
            f"{latency_ms:.1f} api {json.dumps(message)}"
        )

    def start(self) -> None:
        """Start appending log events on a background thread."""
        with self._condition:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stopping = False
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8", newline="\n") as output:
                output.write(self.generate_line() + "\n")
                output.flush()
            self._thread = threading.Thread(target=self._write_loop, name="log-generator", daemon=True)
            self._thread.start()

    def _write_loop(self) -> None:
        with self.path.open("a", encoding="utf-8", newline="\n") as output:
            while True:
                with self._condition:
                    if self._stopping:
                        return
                    version = self._scenario_version
                    interval = self.interval_for_scenario(self._scenario)
                    self._condition.wait_for(
                        lambda: self._stopping or version != self._scenario_version,
                        timeout=interval,
                    )
                    if self._stopping:
                        return
                output.write(self.generate_line() + "\n")
                output.flush()

    def stop(self) -> None:
        """Stop the background writer and wait for its final append."""
        with self._condition:
            self._stopping = True
            self._condition.notify_all()
            thread = self._thread
        if thread is not None:
            thread.join()

    def __enter__(self) -> "LogGenerator":
        self.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.stop()


def main() -> None:
    parser = argparse.ArgumentParser(description="Append synthetic request logs to a file.")
    parser.add_argument("--rate", type=float, default=1.0, help="base events per second")
    parser.add_argument("--scenario", choices=SCENARIOS, default="normal")
    parser.add_argument("--path", default="app.log", help="output log file")
    args = parser.parse_args()

    generator = LogGenerator(path=args.path, rate=args.rate, scenario=args.scenario)
    generator.start()
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        pass
    finally:
        generator.stop()


if __name__ == "__main__":
    main()