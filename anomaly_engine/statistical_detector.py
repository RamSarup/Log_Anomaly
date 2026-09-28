"""Statistical detector: z-scores of the current window vs. the baseline."""

from __future__ import annotations

from typing import Dict, List

from pydantic import BaseModel, Field

from anomaly_engine.models import Baseline, LogWindow, MetricStats, Signal

Z_SIGNAL = 3.0   # |z| at or above this raises a named signal
Z_FLOOR = 1.0    # z at or below this contributes 0 to the score
Z_MAX = 6.0      # z at or above this contributes the full 1.0

# How much each metric can push the score (volume is a weaker indicator).
WEIGHTS: Dict[str, float] = {
    "error_rate": 1.0,
    "avg_latency_ms": 1.0,
    "five_xx_rate": 1.0,
    "request_volume": 0.5,
}


class StatisticalResult(BaseModel):
    score: float = Field(..., ge=0.0, le=1.0)
    signals: List[Signal] = Field(default_factory=list)
    z_scores: Dict[str, float] = Field(default_factory=dict)


def zscore(value: float, stats: MetricStats) -> float:
    return (value - stats.mean) / max(stats.std, 1e-9)


def _scale(z: float) -> float:
    """Map a z-score to 0..1 (0 at z<=1, 1 at z>=6)."""
    return min(max((z - Z_FLOOR) / (Z_MAX - Z_FLOOR), 0.0), 1.0)


def detect(window: LogWindow, baseline: Baseline) -> StatisticalResult:
    features = window.features()
    z = {name: zscore(features[name], baseline.metrics[name]) for name in features}

    signals: List[Signal] = []
    if z["error_rate"] >= Z_SIGNAL:
        signals.append(Signal.ERROR_RATE_SPIKE)
    if z["avg_latency_ms"] >= Z_SIGNAL:
        signals.append(Signal.LATENCY_SPIKE)
    if z["five_xx_rate"] >= Z_SIGNAL:
        signals.append(Signal.FIVE_XX_SPIKE)
    if z["request_volume"] >= Z_SIGNAL:
        signals.append(Signal.VOLUME_SPIKE)
    if z["request_volume"] <= -Z_SIGNAL:
        signals.append(Signal.VOLUME_DROP)

    # Only "bad" directions count: errors/latency/5xx going UP, volume either way.
    contributions = {
        "error_rate": _scale(z["error_rate"]),
        "avg_latency_ms": _scale(z["avg_latency_ms"]),
        "five_xx_rate": _scale(z["five_xx_rate"]),
        "request_volume": _scale(abs(z["request_volume"])),
    }

    # Noisy-OR: several moderate signals compound into a higher score.
    calm = 1.0
    for name, c in contributions.items():
        calm *= 1.0 - WEIGHTS[name] * c
    score = 1.0 - calm

    return StatisticalResult(
        score=round(min(max(score, 0.0), 1.0), 4),
        signals=signals,
        z_scores={k: round(v, 2) for k, v in z.items()},
    )