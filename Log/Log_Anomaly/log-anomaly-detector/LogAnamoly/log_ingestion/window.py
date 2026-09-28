"""Event-time sliding-window aggregation into the anomaly engine's LogWindow."""

import logging
import math
from collections import defaultdict
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

from log_ingestion.models import LogEvent

if TYPE_CHECKING:
    from anomaly_engine.models import LogWindow

logger = logging.getLogger(__name__)
WindowFactory = Callable[..., Any]


def _default_window_factory(**values: object) -> "LogWindow":
    try:
        from anomaly_engine.models import LogWindow
    except ImportError as error:
        raise ImportError(
            "SlidingWindow needs anomaly_engine.models.LogWindow to emit windows; "
            "install the anomaly engine or supply window_factory for tests."
        ) from error
    return LogWindow(**values)


class SlidingWindow:
    """Aggregate event-time windows aligned to Unix-epoch slide boundaries.

    Events are expected in event-time order. A late event that could only affect
    already-emitted windows is skipped with a warning.
    """

    def __init__(
        self,
        duration_seconds: int = 60,
        slide_seconds: int = 10,
        window_factory: WindowFactory | None = None,
    ) -> None:
        if duration_seconds <= 0 or slide_seconds <= 0:
            raise ValueError("window duration and slide interval must be positive")
        if duration_seconds % slide_seconds:
            raise ValueError("window duration must be divisible by slide interval")
        self.duration_seconds = duration_seconds
        self.slide_seconds = slide_seconds
        self._window_slots = duration_seconds // slide_seconds
        self._window_factory = window_factory or _default_window_factory
        self._buckets: dict[int, list[float | int]] = defaultdict(lambda: [0, 0, 0, 0.0])
        self._pending_starts: set[int] = set()
        self._latest_bucket: int | None = None
        self._last_closed_start: int | None = None
        self._timezone_aware: bool | None = None

    def add(self, event: LogEvent) -> list["LogWindow"]:
        """Add one event and return all newly closed, non-empty windows."""
        bucket = self._bucket_for(event.timestamp)
        if self._last_closed_start is not None and bucket <= self._last_closed_start:
            logger.warning("Skipping late event at %s because its windows were already emitted", event.timestamp)
            return []

        totals = self._buckets[bucket]
        totals[0] += 1
        if 400 <= event.status_code <= 599:
            totals[1] += 1
        if 500 <= event.status_code <= 599:
            totals[2] += 1
        totals[3] += event.latency_ms

        for start in range(bucket - self._window_slots + 1, bucket + 1):
            if self._last_closed_start is None or start > self._last_closed_start:
                self._pending_starts.add(start)

        self._latest_bucket = bucket if self._latest_bucket is None else max(self._latest_bucket, bucket)
        return self._collect_ready()

    def advance_watermark(self, timestamp: datetime) -> list["LogWindow"]:
        """Close windows through an event-time watermark, skipping empty ones."""
        bucket = self._bucket_for(timestamp)
        self._latest_bucket = bucket if self._latest_bucket is None else max(self._latest_bucket, bucket)
        return self._collect_ready()

    def _bucket_for(self, timestamp: datetime) -> int:
        aware = timestamp.utcoffset() is not None
        if self._timezone_aware is None:
            self._timezone_aware = aware
        elif aware != self._timezone_aware:
            raise ValueError("cannot mix timezone-aware and naive event timestamps")

        epoch = datetime(1970, 1, 1, tzinfo=timezone.utc) if aware else datetime(1970, 1, 1)
        normalized = timestamp.astimezone(timezone.utc) if aware else timestamp
        return math.floor((normalized - epoch).total_seconds() / self.slide_seconds)

    def _datetime_for(self, bucket: int) -> datetime:
        aware = bool(self._timezone_aware)
        epoch = datetime(1970, 1, 1, tzinfo=timezone.utc) if aware else datetime(1970, 1, 1)
        return epoch + timedelta(seconds=bucket * self.slide_seconds)

    def _collect_ready(self) -> list["LogWindow"]:
        if self._latest_bucket is None:
            return []
        last_ready_start = self._latest_bucket - self._window_slots
        if self._last_closed_start is not None:
            last_ready_start = max(last_ready_start, self._last_closed_start)
        ready_starts = sorted(start for start in self._pending_starts if start <= last_ready_start)
        windows: list["LogWindow"] = []

        for start in ready_starts:
            totals = [0, 0, 0, 0.0]
            for bucket in range(start, start + self._window_slots):
                values = self._buckets.get(bucket)
                if values is not None:
                    totals = [totals[index] + values[index] for index in range(4)]
            total_requests = int(totals[0])
            if total_requests:
                windows.append(
                    self._window_factory(
                        window_start=self._datetime_for(start),
                        window_end=self._datetime_for(start + self._window_slots),
                        total_requests=total_requests,
                        error_count=int(totals[1]),
                        server_error_count=int(totals[2]),
                        avg_latency_ms=float(totals[3]) / total_requests,
                    )
                )
            self._pending_starts.remove(start)
        self._last_closed_start = last_ready_start

        if self._last_closed_start is not None:
            earliest_needed_bucket = self._last_closed_start + 1
            for bucket in tuple(self._buckets):
                if bucket < earliest_needed_bucket:
                    del self._buckets[bucket]

        return windows