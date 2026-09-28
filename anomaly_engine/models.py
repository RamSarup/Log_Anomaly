"""Data contracts for the anomaly engine.

Input : LogWindow      (produced by the windowing teammate)
Output: AnalysisResult (consumed by FastAPI/dashboard and SNS/CloudWatch)
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, model_validator


class Severity(str, Enum):
    NORMAL = "NORMAL"
    WARNING = "WARNING"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Signal(str, Enum):
    ERROR_RATE_SPIKE = "error_rate_spike"
    LATENCY_SPIKE = "latency_spike"
    FIVE_XX_SPIKE = "5xx_spike"
    VOLUME_SPIKE = "volume_spike"
    VOLUME_DROP = "volume_drop"


# Order used everywhere a feature vector is built (ML detector, baseline, tests).
FEATURE_NAMES: List[str] = ["error_rate", "avg_latency_ms", "request_volume", "five_xx_rate"]


# ---------------------------------------------------------------- INPUT
class LogWindow(BaseModel):
    """Aggregated stats for one time window of logs."""

    window_start: Optional[datetime] = None
    window_end: Optional[datetime] = None
    total_requests: int = Field(..., ge=0)
    error_count: int = Field(..., ge=0)           # all failed requests (4xx + 5xx, or as agreed)
    server_error_count: int = Field(0, ge=0)      # 5xx only
    avg_latency_ms: float = Field(..., ge=0)

    @model_validator(mode="after")
    def _check_counts(self) -> "LogWindow":
        if self.error_count > self.total_requests:
            raise ValueError("error_count cannot exceed total_requests")
        if self.server_error_count > self.total_requests:
            raise ValueError("server_error_count cannot exceed total_requests")
        return self

    @property
    def error_rate(self) -> float:
        return self.error_count / self.total_requests if self.total_requests else 0.0

    @property
    def five_xx_rate(self) -> float:
        return self.server_error_count / self.total_requests if self.total_requests else 0.0

    @property
    def request_volume(self) -> float:
        return float(self.total_requests)

    def features(self) -> Dict[str, float]:
        """Named features, keys match FEATURE_NAMES."""
        return {
            "error_rate": self.error_rate,
            "avg_latency_ms": self.avg_latency_ms,
            "request_volume": self.request_volume,
            "five_xx_rate": self.five_xx_rate,
        }

    def feature_vector(self) -> List[float]:
        f = self.features()
        return [f[name] for name in FEATURE_NAMES]


# ------------------------------------------------------------- BASELINE
class MetricStats(BaseModel):
    """Mean and standard deviation of one metric under 'normal' conditions."""

    mean: float
    std: float = Field(..., ge=0)


class Baseline(BaseModel):
    """What 'normal' looks like, per metric."""

    metrics: Dict[str, MetricStats]
    sample_count: int = Field(0, ge=0)   # number of windows the baseline was built from


# --------------------------------------------------------------- OUTPUT
class AnalysisResult(BaseModel):
    """What the engine returns for each window."""

    anomaly: bool
    score: float = Field(..., ge=0.0, le=1.0)          # fused final score
    severity: Severity
    signals: List[Signal] = Field(default_factory=list)
    ml_anomaly: bool = False

    # Explainability / debugging (dashboard can show these)
    statistical_score: float = Field(0.0, ge=0.0, le=1.0)
    ml_score: float = Field(0.0, ge=0.0, le=1.0)
    z_scores: Dict[str, float] = Field(default_factory=dict)