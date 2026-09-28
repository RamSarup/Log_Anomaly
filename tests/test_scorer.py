from anomaly_engine.scorer import fuse
from anomaly_engine.severity import CRITICAL_AT, HIGH_AT


def test_both_high_is_critical():
    assert fuse(0.95, 0.9) >= CRITICAL_AT


def test_stat_only_cannot_be_critical():
    assert fuse(1.0, 0.1) < CRITICAL_AT


def test_ml_only_cannot_be_critical():
    assert fuse(0.1, 1.0) < CRITICAL_AT


def test_volume_only_capped_below_high():
    assert fuse(0.5, 0.9, volume_only=True) < HIGH_AT


def test_normal_stays_low():
    assert fuse(0.05, 0.1) < 0.3