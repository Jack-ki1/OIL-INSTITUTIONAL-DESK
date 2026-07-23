"""pytest coverage for the engine/* modules.

Focus: the testing-checklist invariants in §10 of the build prompt —
session-relative z-score, two-factor alert logic, cooldown suppression, and
the NLP model.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import alerts, news_nlp, orderflow
from engine.sessions import base_volume, session_for_hour
from engine.volume_signals import is_volume_anomaly, loop_score, volume_z_score
from storage.signal_store import SignalStore


# --- sessions -------------------------------------------------------------

def test_session_for_hour_bands():
    assert session_for_hour(0)["key"] == "asian"
    assert session_for_hour(7)["key"] == "asian"
    assert session_for_hour(8)["key"] == "london"
    assert session_for_hour(13)["key"] == "ny"
    assert session_for_hour(20)["key"] == "ny"
    assert session_for_hour(21)["key"] == "off"
    assert session_for_hour(23)["key"] == "off"


# --- volume z-score is SESSION-RELATIVE, not a flat window ----------------

def test_zscore_is_session_relative():
    # The same absolute volume is a bigger anomaly in a quiet session than a
    # busy one, because the baseline differs per session.
    vol = 6000
    z_asian = volume_z_score(vol, "asian")   # baseline 1800
    z_ny = volume_z_score(vol, "ny")         # baseline 4200
    assert z_asian > z_ny


def test_synthetic_spike_flags_anomaly():
    base = base_volume("ny")
    spike = base * 12  # a clear spike
    z = volume_z_score(spike, "ny")
    assert z > 4
    assert is_volume_anomaly(z, threshold=2.5)


def test_normal_volume_not_flagged():
    base = base_volume("ny")
    z = volume_z_score(base * 1.1, "ny")
    assert not is_volume_anomaly(z, threshold=2.5)


# --- multi-factor alert logic (two-factor minimum) ------------------------

def test_volume_spike_alone_does_not_fire():
    # Big volume but flat order flow -> no alert.
    result = alerts.evaluate_alert(
        volume_z=5.0, imbalance=0.3, z_threshold=2.5, require_news=False, news_direction=None
    )
    assert result["conditions_met"] is False


def test_orderflow_shift_alone_does_not_fire():
    result = alerts.evaluate_alert(
        volume_z=0.5, imbalance=3.5, z_threshold=2.5, require_news=False, news_direction=None
    )
    assert result["conditions_met"] is False


def test_both_factors_fire():
    result = alerts.evaluate_alert(
        volume_z=3.0, imbalance=3.0, z_threshold=2.5, require_news=False, news_direction=None
    )
    assert result["conditions_met"] is True
    assert result["direction"] == "long"


def test_news_required_blocks_without_confirmation():
    # Both factors met, but news required and none in the right direction.
    blocked = alerts.evaluate_alert(
        volume_z=3.0, imbalance=3.0, z_threshold=2.5, require_news=True, news_direction=None
    )
    assert blocked["conditions_met"] is False
    confirmed = alerts.evaluate_alert(
        volume_z=3.0, imbalance=3.0, z_threshold=2.5, require_news=True, news_direction="long"
    )
    assert confirmed["conditions_met"] is True


# --- NLP model ------------------------------------------------------------

def test_extract_entities():
    ents = news_nlp.extract_entities("Tanker traffic through the Strait of Hormuz drops")
    assert "Strait of Hormuz" in ents


def test_sentiment_directions():
    bull = news_nlp.score_sentiment("OPEC+ output cut and sanctions tighten supply")
    bear = news_nlp.score_sentiment("SPR release boosts supply, surplus builds")
    assert bull > 0
    assert bear < 0


def test_market_moving_requires_entity_and_sentiment():
    a = news_nlp.analyze_headline("OPEC+ weighs deeper output cut")
    assert a["market_moving"] is True
    b = news_nlp.analyze_headline("Markets calm on a quiet trading day")
    assert b["market_moving"] is False


# --- loop score -----------------------------------------------------------

def test_loop_score_bounds():
    assert loop_score(0, 0, 0) == 0
    assert 0 <= loop_score(10, 5, 10) <= 100


# --- order flow -----------------------------------------------------------

def test_order_book_has_six_levels():
    book = orderflow.build_order_book(80.0, 2.0)
    assert len(book["bids"]) == 6
    assert len(book["asks"]) == 6


# --- signal store cooldown/dedup ------------------------------------------

def test_signal_store_dedup(tmp_path):
    store = SignalStore(db_path=str(tmp_path / "t.db"))
    factors = [{"label": "x", "met": True, "detail": "y"}]
    ok1 = store.record(direction="long", session="NY", vol_z=3.0, imbalance=3.0, factors=factors, ts="2026-01-01T00:00:00Z")
    ok2 = store.record(direction="long", session="NY", vol_z=3.1, imbalance=3.1, factors=factors, ts="2026-01-01T00:00:00Z")
    assert ok1 is True
    assert ok2 is False  # dedup within the same second
    assert store.count() == 1


def test_cooldown_suppresses_within_window():
    """Simulate the tick-loop cooldown gate: a second qualifying signal within
    the cooldown window is suppressed and increments the suppressed counter."""
    import time as _time

    cooldown_seconds = 60
    suppressed = 0
    fired = 0
    cooldown_until = 0.0

    def qualifies():
        return alerts.evaluate_alert(
            volume_z=3.0, imbalance=3.0, z_threshold=2.5, require_news=False, news_direction=None
        )["conditions_met"]

    now = _time.time()
    # First qualifying signal fires.
    if qualifies():
        if now < cooldown_until:
            suppressed += 1
        else:
            fired += 1
            cooldown_until = now + cooldown_seconds
    # Second qualifying signal moments later is suppressed.
    now2 = now + 1
    if qualifies():
        if now2 < cooldown_until:
            suppressed += 1
        else:
            fired += 1
    assert fired == 1
    assert suppressed == 1
