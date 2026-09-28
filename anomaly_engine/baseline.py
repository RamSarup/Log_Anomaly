"""Baseline: learn what 'normal' looks like from healthy log windows."""

from __future__ import annotations

from typing import Dict, Sequence

import numpy as np

from anomaly_engine.models import FEATURE_NAMES, Baseline, LogWindow, MetricStats

# Minimum std per metric. Without a floor, a perfectly steady baseline
# (std = 0) would make any tiny change look like an infinite z-score.
MIN_STD: Dict[str, float] = {
    "error_rate": 0.005,      # 0.5 percentage points
    "avg_latency_ms": 10.0,   # 10 ms
    "request_volume": 5.0,    # 5 requests
    "five_xx_rate": 0.002,    # 0.2 percentage points
}

MIN_WINDOWS = 5


def build_baseline(windows: Sequence[LogWindow]) -> Baseline:
    """Compute mean/std of every feature across the given normal windows."""
    if len(windows) < MIN_WINDOWS:
        raise ValueError(
            f"Need at least {MIN_WINDOWS} windows to build a baseline, got {len(windows)}"
        )

    matrix = np.array([w.feature_vector() for w in windows], dtype=float)
    means = matrix.mean(axis=0)
    stds = matrix.std(axis=0, ddof=1)  # sample std

    metrics = {
        name: MetricStats(mean=float(m), std=float(max(s, MIN_STD[name])))
        for name, m, s in zip(FEATURE_NAMES, means, stds)
    }
    return Baseline(metrics=metrics, sample_count=len(windows))


def default_baseline() -> Baseline:
    """Fallback for cold start, before enough real windows exist."""
    defaults = {
        "error_rate": (0.01, 0.005),
        "avg_latency_ms": (180.0, 30.0),
        "request_volume": (1000.0, 100.0),
        "five_xx_rate": (0.002, 0.002),
    }
    return Baseline(
        metrics={k: MetricStats(mean=m, std=s) for k, (m, s) in defaults.items()},
        sample_count=0,
    )