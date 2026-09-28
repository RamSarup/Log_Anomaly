from dataclasses import dataclass
from datetime import datetime


@dataclass
class WindowRecord:
    window_start: datetime
    window_end: datetime
    total_requests: int
    error_count: int
    server_error_count: int
    avg_latency_ms: float


def make_window(**values: object) -> WindowRecord:
    return WindowRecord(**values)