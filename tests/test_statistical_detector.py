from anomaly_engine.baseline import default_baseline
from anomaly_engine.models import LogWindow, Signal
from anomaly_engine.statistical_detector import detect

BASE = default_baseline()


def win(requests=1000, errors=10, latency=200.0, server_errors=2):
    return LogWindow(
        total_requests=requests,
        error_count=errors,
        server_error_count=server_errors,
        avg_latency_ms=latency,
    )


def test_normal_window():
    r = detect(win(), BASE)
    assert r.signals == []
    assert r.score < 0.2


def test_error_and_latency_spike():
    r = detect(win(errors=120, latency=2200.0, server_errors=80), BASE)
    assert Signal.ERROR_RATE_SPIKE in r.signals
    assert Signal.LATENCY_SPIKE in r.signals
    assert r.score > 0.9


def test_volume_drop():
    r = detect(win(requests=200, errors=2, server_errors=0), BASE)
    assert Signal.VOLUME_DROP in r.signals


def test_faster_latency_is_not_flagged():
    r = detect(win(latency=50.0), BASE)
    assert Signal.LATENCY_SPIKE not in r.signals
    assert r.score < 0.2