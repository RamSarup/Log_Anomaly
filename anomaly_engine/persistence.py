"""Persistence gate: alert only after N bad windows in a row."""

from anomaly_engine.models import AnalysisResult, Severity

BAD_LEVELS = (Severity.HIGH, Severity.CRITICAL)


class PersistenceGate:
    def __init__(self, required: int = 3):
        self.required = required
        self.streak = 0

    def update(self, result: AnalysisResult) -> bool:
        """Feed one result per window. Returns True when an alert should fire."""
        if result.severity in BAD_LEVELS:
            self.streak += 1
        else:
            self.streak = 0
        return self.streak >= self.required