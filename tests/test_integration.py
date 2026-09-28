from anomaly_engine.engine import AnomalyEngine
from anomaly_engine.ml_detector import synthetic_normal_windows
from anomaly_engine.models import LogWindow, Severity

ENGINE = AnomalyEngine.default()

BAD = (Severity.HIGH, Severity.CRITICAL)


def incident_window():
    return LogWindow(
        total_requests=1000,
        error_count=120,
        server_error_count=80,
        avg_latency_ms=2200.0,
    )


def test_full_stream_normal_incident_recovery():
    before = synthetic_normal_windows(30, seed=1)
    incident = [incident_window() for _ in range(5)]
    after = synthetic_normal_windows(10, seed=2)

    # 1. normal traffic: no serious alerts
    for w in before:
        assert ENGINE.analyze(w).severity not in BAD

    # 2. incident: every window is CRITICAL
    for w in incident:
        assert ENGINE.analyze(w).severity == Severity.CRITICAL

    # 3. recovery: back to no serious alerts straight away
    for w in after:
        assert ENGINE.analyze(w).severity not in BAD


def test_incident_detected_on_first_window():
    r = ENGINE.analyze(incident_window())
    assert r.anomaly is True
    assert r.severity == Severity.CRITICAL