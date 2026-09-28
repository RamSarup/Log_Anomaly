import pytest

from anomaly_engine.ml_detector import MLDetector, synthetic_normal_windows
from anomaly_engine.models import LogWindow


def make_detector():
    return MLDetector().fit(synthetic_normal_windows(300))


def test_normal_window_not_anomalous():
    r = make_detector().predict(
        LogWindow(total_requests=1000, error_count=10, server_error_count=2, avg_latency_ms=190.0)
    )
    assert r.anomaly is False
    assert r.score < 0.5


def test_spike_window_is_anomalous():
    r = make_detector().predict(
        LogWindow(total_requests=1000, error_count=120, server_error_count=80, avg_latency_ms=2200.0)
    )
    assert r.anomaly is True
    assert r.score > 0.5


def test_predict_before_fit_raises():
    with pytest.raises(RuntimeError):
        MLDetector().predict(
            LogWindow(total_requests=1000, error_count=10, avg_latency_ms=190.0)
        )


def test_too_few_training_windows_raises():
    with pytest.raises(ValueError):
        MLDetector().fit(synthetic_normal_windows(5))