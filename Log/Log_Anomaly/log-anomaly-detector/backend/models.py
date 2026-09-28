"""Shared event data model used between event sources and dashboard clients."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class LogEvent(BaseModel):
	"""A single log-derived event sent to the live dashboard."""

	timestamp: datetime
	level: Literal["INFO", "WARNING", "ERROR"]
	service: str
	message: str
	error_rate: float = Field(ge=0, le=1, description="Fraction from 0.0 to 1.0")
	baseline: float = Field(ge=0, le=1)
	deviation: float
	severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
	is_anomaly: bool
