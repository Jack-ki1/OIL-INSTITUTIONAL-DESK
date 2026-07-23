"""Trading-session tagging + prior-session range tracking.

Ported from the earlier Streamlit project's session logic and the JSX
``sessionForHour`` helper. A "session" is a UTC hour band (Asian / London /
New York / Off-hours). Volume baselines are session-relative, so every other
signal depends on getting this mapping right.
"""
from __future__ import annotations

from datetime import datetime, timezone

import config


def session_for_hour(hour: int) -> dict:
    """Return the session dict whose [start, end) band contains ``hour`` (UTC).

    Falls back to the Off-hours session, mirroring the JSX ``|| SESSIONS[3]``.
    """
    for s in config.SESSIONS:
        if s["start"] <= hour < s["end"]:
            return s
    return config.SESSIONS[3]


def session_for_time(when: datetime | None = None) -> dict:
    when = when or datetime.now(timezone.utc)
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return session_for_hour(when.astimezone(timezone.utc).hour)


def base_volume(session_key: str) -> float:
    """Session-relative baseline volume (same numbers as the JSX simulation)."""
    return float(config.SESSION_BASE_VOLUME.get(session_key, config.SESSION_BASE_VOLUME["off"]))


class PriorSessionRange:
    """Tracks the high/low of the *previous* completed session per key.

    Used for breakout-of-prior-session-range detection. Feed it (session_key,
    price) each tick; when the session key changes it rolls the current range
    into ``prior`` and starts a fresh one.
    """

    def __init__(self) -> None:
        self._current_key: str | None = None
        self._cur_high: float | None = None
        self._cur_low: float | None = None
        self.prior: dict[str, dict[str, float]] = {}

    def update(self, session_key: str, price: float) -> None:
        if session_key != self._current_key:
            if self._current_key is not None and self._cur_high is not None:
                self.prior[self._current_key] = {"high": self._cur_high, "low": self._cur_low}
            self._current_key = session_key
            self._cur_high = price
            self._cur_low = price
        else:
            self._cur_high = max(self._cur_high, price)
            self._cur_low = min(self._cur_low, price)

    def breakout(self, session_key: str, price: float) -> str | None:
        """Return 'up'/'down' if price breaks the prior session's range, else None."""
        rng = self.prior.get(session_key)
        if not rng:
            return None
        if price > rng["high"]:
            return "up"
        if price < rng["low"]:
            return "down"
        return None
