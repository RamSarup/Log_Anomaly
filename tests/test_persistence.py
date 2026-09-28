from anomaly_engine.models import AnalysisResult, Severity
from anomaly_engine.persistence import PersistenceGate


def result(severity):
    return AnalysisResult(anomaly=severity != Severity.NORMAL, score=0.9, severity=severity)


def test_alert_only_after_required_streak():
    gate = PersistenceGate(required=3)
    assert gate.update(result(Severity.CRITICAL)) is False
    assert gate.update(result(Severity.CRITICAL)) is False
    assert gate.update(result(Severity.CRITICAL)) is True


def test_normal_window_resets_streak():
    gate = PersistenceGate(required=3)
    gate.update(result(Severity.CRITICAL))
    gate.update(result(Severity.CRITICAL))
    gate.update(result(Severity.NORMAL))
    assert gate.update(result(Severity.CRITICAL)) is False


def test_warning_does_not_count():
    gate = PersistenceGate(required=2)
    gate.update(result(Severity.WARNING))
    assert gate.update(result(Severity.WARNING)) is False