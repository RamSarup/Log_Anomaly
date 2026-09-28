"""Engine: the single entry point. engine.analyze(window) -> AnalysisResult."""

from __future__ import annotations

from typing import Sequence

from anomaly_engine.baseline import build_baseline, default_baseline
from anomaly_engine.ml_detector import MLDetector, synthetic_normal_windows
from anomaly_engine.models import AnalysisResult, Baseline, LogWindow, Severity, Signal
from anomaly_engine.scorer import fuse
from anomaly_engine.severity import score_to_severity
from anomaly_engine.statistical_detector import detect


class AnomalyEngine:
    def __init__(self, baseline: Baseline, ml: MLDetector):
        self.baseline = baseline
        self.ml = ml

    @classmethod
    def default(cls) -> "AnomalyEngine":
        """Cold start: default baseline + ML trained on synthetic healthy traffic."""
        ml = MLDetector().fit(synthetic_normal_windows(300))
        return cls(default_baseline(), ml)

    @classmethod
    def from_history(cls, windows: Sequence[LogWindow]) -> "AnomalyEngine":
        """Learn baseline and ML model from real healthy windows (needs 30+)."""
        return cls(build_baseline(windows), MLDetector().fit(windows))

    def analyze(self, window: LogWindow) -> AnalysisResult:
        stat = detect(window, self.baseline)
        ml = self.ml.predict(window)

        # A traffic surge with no error/latency/5xx signal (e.g. a flash sale).
        volume_only = stat.signals == [Signal.VOLUME_SPIKE]

        score = fuse(stat.score, ml.score, volume_only=volume_only)
        severity = score_to_severity(score)

        return AnalysisResult(
            anomaly=severity != Severity.NORMAL,
            score=score,
            severity=severity,
            signals=stat.signals,
            ml_anomaly=ml.anomaly,
            statistical_score=stat.score,
            ml_score=ml.score,
            z_scores=stat.z_scores,
        )