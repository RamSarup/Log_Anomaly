"""Configuration shared by the synthetic log generator."""

from dataclasses import dataclass
from typing import Literal

Scenario = Literal[
    "normal",
    "error_spike",
    "latency_spike",
    "traffic_spike",
    "database_failure",
]

SCENARIOS: tuple[Scenario, ...] = (
    "normal",
    "error_spike",
    "latency_spike",
    "traffic_spike",
    "database_failure",
)


@dataclass(frozen=True, slots=True)
class ScenarioProfile:
    statuses: tuple[int, ...]
    latency_min_ms: float
    latency_max_ms: float
    traffic_multiplier: float = 1.0
    database_messages: tuple[str, ...] = ()


PROFILES: dict[Scenario, ScenarioProfile] = {
    "normal": ScenarioProfile(
        statuses=(200, 200, 201, 200, 204, 200, 200, 200, 404, 200, 200, 200, 500, 200, 201, 200, 200, 204, 200, 200),
        latency_min_ms=12.0,
        latency_max_ms=350.0,
    ),
    "error_spike": ScenarioProfile(
        statuses=(500, 404, 503, 200, 429, 500, 400, 503, 200, 502),
        latency_min_ms=20.0,
        latency_max_ms=500.0,
    ),
    "latency_spike": ScenarioProfile(
        statuses=(200, 200, 201, 204, 200, 404, 200, 200),
        latency_min_ms=1200.0,
        latency_max_ms=5000.0,
    ),
    "traffic_spike": ScenarioProfile(
        statuses=(200, 200, 201, 200, 204, 200, 200, 200, 404, 200, 200, 200, 500, 200, 201, 200, 200, 204, 200, 200),
        latency_min_ms=12.0,
        latency_max_ms=350.0,
        traffic_multiplier=5.0,
    ),
    "database_failure": ScenarioProfile(
        statuses=(500, 503, 500, 500, 200, 500, 503, 500, 500, 500),
        latency_min_ms=300.0,
        latency_max_ms=2200.0,
        database_messages=(
            "Database timeout",
            "Database connection refused",
            "Database unavailable",
        ),
    ),
}