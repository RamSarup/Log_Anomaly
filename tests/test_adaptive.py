from anomaly_engine.adaptive import AdaptiveEngine
from anomaly_engine.engine import AnomalyEngine
from anomaly_engine.ml_detector import synthetic_normal_windows
from anomaly_engine.models import LogWindow

NORMAL = LogWindow(total_requests=1000, error_count=10,
                   server_error_count=2, avg_latency_ms=190)
INCIDENT = LogWindow(total_requests=1000, error_count=120,
                     server_error_count=80, avg_latency_ms=2200)


def test_incident_window_is_not_learned():
    a = AdaptiveEngine(AnomalyEngine.default())
    a.analyze(INCIDENT)
    assert len(a.history) == 0


def test_normal_window_is_learned():
    a = AdaptiveEngine(AnomalyEngine.default())
    a.analyze(NORMAL)
    assert len(a.history) == 1


def test_baseline_refreshes_from_real_windows():
    a = AdaptiveEngine(AnomalyEngine.default(), refresh_every=30, min_history=30)
    assert a.engine.baseline.sample_count == 0
    for w in synthetic_normal_windows(60):
        a.analyze(w)
    assert a.engine.baseline.sample_count >= 30