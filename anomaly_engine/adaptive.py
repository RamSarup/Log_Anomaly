"""Adaptive engine: keeps learning, but only from windows scored NORMAL."""

from collections import deque

from anomaly_engine.baseline import build_baseline
from anomaly_engine.engine import AnomalyEngine
from anomaly_engine.ml_detector import MLDetector
from anomaly_engine.models import AnalysisResult, LogWindow, Severity


class AdaptiveEngine:
    def __init__(self, engine: AnomalyEngine, max_history: int = 500,
                 refresh_every: int = 50, min_history: int = 30):
        self.engine = engine
        self.history = deque(maxlen=max_history)
        self.refresh_every = refresh_every
        self.min_history = min_history
        self._since_refresh = 0

    def analyze(self, window: LogWindow) -> AnalysisResult:
        result = self.engine.analyze(window)

        # Only healthy windows are allowed to shape the baseline.
        if result.severity == Severity.NORMAL:
            self.history.append(window)
            self._since_refresh += 1
            if (self._since_refresh >= self.refresh_every
                    and len(self.history) >= self.min_history):
                self._refresh()

        return result

    def _refresh(self) -> None:
        windows = list(self.history)
        self.engine.baseline = build_baseline(windows)
        self.engine.ml = MLDetector().fit(windows)
        self._since_refresh = 0