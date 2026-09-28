"""Bridge the real log-ingestion pipeline to dashboard event payloads."""

import asyncio
import logging
import sys
from collections.abc import AsyncIterator
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "LogAnamoly"))
sys.path.insert(0, str(PROJECT_ROOT / "detection"))

from anomaly_engine.engine import AnomalyEngine
from anomaly_engine.models import AnalysisResult, LogWindow
from log_ingestion.models import LogEvent as IngestedLogEvent
from log_ingestion.generator import LogGenerator
from log_ingestion.parser import parse_log_line
from log_ingestion.tailer import LogTailer
from log_ingestion.window import SlidingWindow

from backend.aws_services import AwsPublisher

logger = logging.getLogger(__name__)
LOG_PATH = PROJECT_ROOT / "logs" / "application.log"


def _event_payload(event: IngestedLogEvent) -> dict:
	"""Keep the existing frontend event contract for raw log events."""
	error_rate = 1.0 if event.status_code >= 400 else 0.0
	return {
		"type": "event",
		"timestamp": event.timestamp.isoformat(),
		"level": event.level,
		"service": event.service,
		"message": event.message,
		"error_rate": error_rate,
		"baseline": 0.01,
		"deviation": error_rate - 0.01,
		"severity": "WARNING" if event.status_code >= 400 else "NORMAL",
		"is_anomaly": False,
	}


def _analysis_payload(window: LogWindow, result: AnalysisResult) -> dict:
	"""Adapt an aggregate result to the locked dashboard event shape."""
	return {
		"type": "analysis",
		"timestamp": (window.window_end or window.window_start).isoformat() if (window.window_end or window.window_start) else None,
		"level": "ERROR" if result.anomaly else "INFO",
		"service": "aggregate",
		"message": ", ".join(signal.value for signal in result.signals) or "Window within baseline",
		"error_rate": window.error_rate,
		"baseline": 0.01,
		"deviation": result.score,
		"severity": result.severity.value,
		"is_anomaly": result.anomaly,
		"analysis": result.model_dump(mode="json"),
		"metrics": {
			"total_requests": window.total_requests,
			"error_count": window.error_count,
			"server_error_count": window.server_error_count,
			"error_rate": window.error_rate,
			"five_xx_rate": window.five_xx_rate,
			"avg_latency_ms": window.avg_latency_ms,
		},
	}


async def event_stream(
	path: str | Path = LOG_PATH,
	aws_publisher: AwsPublisher | None = None,
) -> AsyncIterator[dict]:
	"""Yield raw events and completed analysis windows from the real pipeline."""
	tailer = LogTailer(path)
	windowing = SlidingWindow(duration_seconds=60, slide_seconds=10)
	engine = AnomalyEngine.default()
	publisher = aws_publisher or AwsPublisher.from_environment()

	try:
		while True:
			lines = await asyncio.to_thread(tailer.read_available)
			for line in lines:
				event = parse_log_line(line)
				if event is None:
					continue
				yield _event_payload(event)
				for window in windowing.add(event):
					result = engine.analyze(window)
					await asyncio.to_thread(publisher.publish, result, window)
					yield _analysis_payload(window, result)
			await asyncio.sleep(0.1)
	finally:
		tailer.close()
