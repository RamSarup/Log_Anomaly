import pytest

from anomaly_engine.baseline import MIN_STD, build_baseline, default_baseline
from anomaly_engine.models import LogWindow


def make_window(requests=1000, errors=10, latency=180.0, server_errors=2):
    return LogWindow(
        total_requests=requests,
        error_count=errors,
        server_error_count=server_errors,
        avg_latency_ms=latency,
    )


def test_baseline_means():
    windows = [make_window(errors=10, latency=180.0) for _ in range(10)]
    b = build_baseline(windows)
    assert b.sample_count == 10
    assert b.metrics["error_rate"].mean == pytest.approx(0.01)
    assert b.metrics["avg_latency_ms"].mean == pytest.approx(180.0)


def test_std_floor_applied_for_constant_data():
    windows = [make_window() for _ in range(10)]
    b = build_baseline(windows)
    for name, stats in b.metrics.items():
        assert stats.std >= MIN_STD[name]


def test_std_reflects_variation():
    windows = [make_window(latency=100.0 + 20 * i) for i in range(10)]
    b = build_baseline(windows)
    assert b.metrics["avg_latency_ms"].std > 30


def test_too_few_windows_raises():
    with pytest.raises(ValueError):
        build_baseline([make_window() for _ in range(2)])


def test_default_baseline_has_all_features():
    b = default_baseline()
    assert set(b.metrics) == set(MIN_STD)