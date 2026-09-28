"""Score fusion: combine the statistical score and the ML score."""

from anomaly_engine.severity import CRITICAL_AT, HIGH_AT

STAT_WEIGHT = 0.6
ML_WEIGHT = 0.4
AGREEMENT_MIN = 0.3


def fuse(stat_score: float, ml_score: float, volume_only: bool = False) -> float:
    score = STAT_WEIGHT * stat_score + ML_WEIGHT * ml_score

    # One detector alone cannot make a window CRITICAL.
    if min(stat_score, ml_score) < AGREEMENT_MIN:
        score = min(score, CRITICAL_AT - 0.01)

    # Volume changing alone is not an incident (flash sale).
    if volume_only:
        score = min(score, HIGH_AT - 0.01)

    return round(min(max(score, 0.0), 1.0), 4)