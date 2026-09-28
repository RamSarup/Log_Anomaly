"""Models owned by the log-ingestion layer."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class LogEvent:
    timestamp: datetime
    level: str
    status_code: int
    latency_ms: float
    service: str
    message: str