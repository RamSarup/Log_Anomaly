from anomaly_engine.engine import AnomalyEngine
from anomaly_engine.models import LogWindow, Severity, Signal

ENGINE = AnomalyEngine.default()


def win(requests=1000, errors=10, server_errors=2, latency=190.0):
    return LogWindow(
        total_requests=requests,
        error_count=errors,
        server_error_count=server_errors,
        avg_latency_ms=latency,
    )


def test_normal_window():
    r = ENGINE.analyze(win())
    assert r.severity == Severity.NORMAL
    assert r.anomaly is False


def test_incident_is_critical():
    r = ENGINE.analyze(win(errors=120, server_errors=80, latency=2200.0))
    assert r.severity == Severity.CRITICAL
    assert r.anomaly is True
    assert Signal.ERROR_RATE_SPIKE in r.signals
    assert Signal.LATENCY_SPIKE in r.signals
    assert r.ml_anomaly is True


def test_flash_sale_not_high_or_critical():
    # 5x traffic, errors and latency still healthy
    r = ENGINE.analyze(win(requests=5000, errors=50, server_errors=10, latency=190.0))
    assert r.severity not in (Severity.HIGH, Severity.CRITICAL)


def test_result_is_json_ready():
    d = ENGINE.analyze(win()).model_dump(mode="json")
    assert {"anomaly", "score", "severity", "signals", "ml_anomaly"} <= set(d)