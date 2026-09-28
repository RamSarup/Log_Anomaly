"""ML detector: Isolation Forest over all features together."""

from __future__ import annotations

import math
from typing import List, Sequence

import numpy as np
from pydantic import BaseModel, Field
from sklearn.ensemble import IsolationForest

from anomaly_engine.models import LogWindow

MIN_TRAIN_WINDOWS = 30
ML_THRESHOLD = 0.5   # score at or above this counts as ml_anomaly


class MLResult(BaseModel):
    score: float = Field(..., ge=0.0, le=1.0)
    anomaly: bool


class MLDetector:
    def __init__(self, contamination: float = 0.01, random_state: int = 42):
        self.model = IsolationForest(
            n_estimators=200,
            contamination=contamination,
            random_state=random_state,
        )
        self.is_fitted = False

    def fit(self, windows: Sequence[LogWindow]) -> "MLDetector":
        if len(windows) < MIN_TRAIN_WINDOWS:
            raise ValueError(
                f"Need at least {MIN_TRAIN_WINDOWS} windows to train, got {len(windows)}"
            )
        X = np.array([w.feature_vector() for w in windows], dtype=float)
        self.model.fit(X)
        self.is_fitted = True
        return self

    def predict(self, window: LogWindow) -> MLResult:
        if not self.is_fitted:
            raise RuntimeError("MLDetector must be fitted before predict()")
        X = np.array([window.feature_vector()], dtype=float)
        d = float(self.model.decision_function(X)[0])   # >0 normal, <0 anomalous
        score = 1.0 / (1.0 + math.exp(15.0 * d))        # squash to 0..1
        return MLResult(score=round(score, 4), anomaly=score >= ML_THRESHOLD)


def synthetic_normal_windows(n: int = 300, seed: int = 0) -> List[LogWindow]:
    """Fake healthy traffic, for cold start and for tests."""
    rng = np.random.default_rng(seed)
    windows: List[LogWindow] = []
    for _ in range(n):
        requests = max(int(rng.normal(1000, 100)), 1)
        error_rate = float(np.clip(rng.normal(0.01, 0.003), 0.0, 1.0))
        five_xx_rate = float(np.clip(rng.normal(0.002, 0.001), 0.0, 1.0))
        errors = int(round(requests * error_rate))
        server_errors = min(errors, int(round(requests * five_xx_rate)))
        latency = max(float(rng.normal(180, 25)), 1.0)
        windows.append(
            LogWindow(
                total_requests=requests,
                error_count=errors,
                server_error_count=server_errors,
                avg_latency_ms=latency,
            )
        )
    return windows