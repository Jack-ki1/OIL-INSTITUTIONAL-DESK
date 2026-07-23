"""Volume z-score, breakout detection, and the composite Loop Score.

The z-score is computed *relative to the session's baseline* (not a flat
rolling window) so that, e.g., an ordinary NY-session print isn't flagged just
because it's larger than a quiet Asian-session print. This matches the
methodology validated in the earlier Streamlit project's ``tests/test_sessions.py``.
"""
from __future__ import annotations

from engine.sessions import base_volume

# Standard deviation of session volume expressed as a fraction of the baseline
# mean. 0.32 reproduces the JSX simulation's ``baseVol * 0.32`` denominator.
VOLUME_STD_FRACTION = 0.32


def volume_z_score(volume: float, session_key: str, std_fraction: float = VOLUME_STD_FRACTION) -> float:
    """Session-relative z-score: (volume - baseline) / (baseline * std_fraction)."""
    baseline = base_volume(session_key)
    denom = baseline * std_fraction
    if denom == 0:
        return 0.0
    return (volume - baseline) / denom


def is_volume_anomaly(z_score: float, threshold: float) -> bool:
    return z_score >= threshold


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def loop_score(volume_z: float, imbalance: float, news_count: int) -> int:
    """Composite 0-100 'Loop Score'. Ported from the JSX OverviewTab formula.

    loop = clamp(volume_z, 0, 4)/4 * 60 + (|imbalance|>2 ? 25 : 0) + min(news, 3)*5
    """
    score = (
        clamp(volume_z, 0.0, 4.0) / 4.0 * 60.0
        + (25.0 if abs(imbalance) > 2.0 else 0.0)
        + min(news_count, 3) * 5.0
    )
    return int(clamp(round(score), 0, 100))
