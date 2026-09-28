from anomaly_engine.models import Severity
from anomaly_engine.severity import score_to_severity


def test_levels():
    assert score_to_severity(0.05) == Severity.NORMAL
    assert score_to_severity(0.45) == Severity.WARNING
    assert score_to_severity(0.70) == Severity.HIGH
    assert score_to_severity(0.87) == Severity.CRITICAL


def test_boundaries():
    assert score_to_severity(0.30) == Severity.WARNING
    assert score_to_severity(0.60) == Severity.HIGH
    assert score_to_severity(0.80) == Severity.CRITICAL