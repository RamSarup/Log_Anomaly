"""Severity: turn a final score (0..1) into a severity level."""

from anomaly_engine.models import Severity

WARNING_AT = 0.30
HIGH_AT = 0.60
CRITICAL_AT = 0.80


def score_to_severity(score: float) -> Severity:
    if score >= CRITICAL_AT:
        return Severity.CRITICAL
    if score >= HIGH_AT:
        return Severity.HIGH
    if score >= WARNING_AT:
        return Severity.WARNING
    return Severity.NORMAL