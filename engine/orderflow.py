"""Simulated order-book imbalance, iceberg detection, and dark-pool prints.

ALWAYS SIMULATED — no free or retail data source provides real Level 2 depth,
iceberg orders, or dark-pool/block prints, so these stay simulated in both
Live and Simulated mode and must be badged SIM. The logic is ported directly
from the JSX simulation engine (same random ranges, same clip-tracking).
"""
from __future__ import annotations

import random
from datetime import datetime, timezone


def _rand(lo: float, hi: float) -> float:
    return lo + random.random() * (hi - lo)


def _fmt2(n: float) -> float:
    return round(n * 100) / 100


def simulate_imbalance(is_spike: bool) -> float:
    """Order-book imbalance ratio. Large one-sided on spikes, else near-flat."""
    if is_spike:
        mag = _rand(2.2, 4.5)
        return mag if random.random() > 0.5 else -mag
    return _rand(-1.4, 1.4)


def build_order_book(mid: float, imbalance: float, levels: int = 6) -> dict:
    """6 bid + 6 ask levels. Sizes skew to the heavy side of the imbalance."""
    bids = [
        {
            "price": _fmt2(mid - 0.02 * (i + 1)),
            "size": round(_rand(200, 1800) * (1.6 if imbalance < 0 else 1)),
        }
        for i in range(levels)
    ]
    asks = [
        {
            "price": _fmt2(mid + 0.02 * (i + 1)),
            "size": round(_rand(200, 1800) * (1.6 if imbalance > 0 else 1)),
        }
        for i in range(levels)
    ]
    return {"bids": bids, "asks": asks}


class IcebergTracker:
    """Tracks candidate price levels receiving repeated same-side clips.

    A level confirmed with 4+ clips inside a rolling window is an iceberg
    signature (a large resting order being worked in slices). Ported from the
    JSX ``icebergCandidates`` ref logic.
    """

    WINDOW_TICKS = 45
    CONFIRM_CLIPS = 4

    def __init__(self) -> None:
        self._candidates: list[dict] = []

    def update(self, tick: int, mid: float) -> list[dict]:
        """Advance one tick; return any *newly confirmed* icebergs this tick."""
        if random.random() < 0.35:
            lvl = _fmt2(mid + _rand(-0.06, 0.06))
            existing = next((c for c in self._candidates if abs(c["price"] - lvl) < 0.015), None)
            if existing:
                existing["clips"] += 1
                existing["last_seen"] = tick
            elif random.random() < 0.4:
                self._candidates.append(
                    {"price": lvl, "clips": 1, "last_seen": tick, "logged": False}
                )

        self._candidates = [c for c in self._candidates if tick - c["last_seen"] < self.WINDOW_TICKS]

        confirmed = [c for c in self._candidates if c["clips"] >= self.CONFIRM_CLIPS and not c["logged"]]
        for c in confirmed:
            c["logged"] = True
        now = datetime.now(timezone.utc).isoformat()
        return [
            {"price": c["price"], "clips": c["clips"], "time": now}
            for c in confirmed
        ]


def maybe_dark_pool_print(mid: float, probability: float = 0.07) -> dict | None:
    """Low-probability large off-book print. Ported from the JSX version."""
    if random.random() >= probability:
        return None
    return {
        "size": round(_rand(5000, 25000)),
        "price": _fmt2(mid + _rand(-0.1, 0.1)),
        "venue": random.choice(["OTC Block", "Dark Pool Print", "Cross Network"]),
        "time": datetime.now(timezone.utc).isoformat(),
    }
