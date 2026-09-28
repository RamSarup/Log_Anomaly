"""Parser for the deterministic synthetic request-log format."""

import json
import logging
import math
import re
from datetime import datetime

from log_ingestion.models import LogEvent

logger = logging.getLogger(__name__)
_LINE_PATTERN = re.compile(
    r'^\s*(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+("(?:\\.|[^"\\])*")\s*$'
)


def parse_log_line(line: str) -> LogEvent | None:
    """Parse a line of the form TIMESTAMP LEVEL STATUS LATENCY SERVICE JSON_MESSAGE."""
    match = _LINE_PATTERN.fullmatch(line.rstrip("\r\n"))
    if match is None:
        logger.warning("Skipping malformed log line: expected six fields and a quoted message")
        return None

    timestamp_text, level, status_text, latency_text, service, message_text = match.groups()
    try:
        timestamp = datetime.fromisoformat(timestamp_text.replace("Z", "+00:00"))
    except ValueError:
        logger.warning("Skipping malformed log line: invalid timestamp %r", timestamp_text)
        return None

    if not level or not service:
        logger.warning("Skipping malformed log line: level and service must not be empty")
        return None

    try:
        status_code = int(status_text)
    except ValueError:
        logger.warning("Skipping malformed log line: invalid status code %r", status_text)
        return None
    if not 100 <= status_code <= 599:
        logger.warning("Skipping malformed log line: status code out of range %r", status_text)
        return None

    try:
        latency_ms = float(latency_text)
    except ValueError:
        logger.warning("Skipping malformed log line: invalid latency %r", latency_text)
        return None
    if not math.isfinite(latency_ms) or latency_ms < 0:
        logger.warning("Skipping malformed log line: latency must be finite and non-negative")
        return None

    try:
        message = json.loads(message_text)
    except json.JSONDecodeError:
        logger.warning("Skipping malformed log line: message is not a valid JSON string")
        return None
    if not isinstance(message, str):
        logger.warning("Skipping malformed log line: message must be a string")
        return None

    return LogEvent(
        timestamp=timestamp,
        level=level,
        status_code=status_code,
        latency_ms=latency_ms,
        service=service,
        message=message,
    )