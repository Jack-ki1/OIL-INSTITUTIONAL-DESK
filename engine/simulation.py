"""Background tick loop: produces the single unified snapshot every N seconds.

This is the single source of truth for the whole app (see §3 of the build
prompt). One background thread runs the loop; a thread-safe holder exposes the
latest snapshot to the SSE endpoint and REST API. Every page's JS subscribes to
the same snapshot and reads the fields it needs.

Simulated mode is ported faithfully from the JSX ``useMarketSimulation`` hook
(same random ranges, iceberg/dark-pool logic, headline pool). Live mode swaps
in real price/volume (yfinance) and real news (NewsAPI) while keeping order
flow simulated.
"""
from __future__ import annotations

import random
import threading
import time
from datetime import datetime, timezone

import config
from engine import alerts as alerts_engine
from engine import orderflow
from engine.news_nlp import analyze_headline
from engine.sessions import PriorSessionRange, base_volume, session_for_time
from engine.volume_signals import loop_score, volume_z_score


def _rand(lo: float, hi: float) -> float:
    return lo + random.random() * (hi - lo)


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _fmt2(n: float) -> float:
    return round(n * 100) / 100


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class SnapshotHolder:
    """Thread-safe holder for the latest snapshot dict."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._snapshot: dict | None = None

    def set(self, snapshot: dict) -> None:
        with self._lock:
            self._snapshot = snapshot

    def get(self) -> dict | None:
        with self._lock:
            return self._snapshot


class MarketSimulation:
    """Owns runtime config, the tick loop, and per-tick engine state."""

    def __init__(self, store=None) -> None:
        self.holder = SnapshotHolder()
        self.store = store

        # Runtime-tunable alert config (mutated via the REST API).
        self.z_threshold = config.DEFAULT_Z_THRESHOLD
        self.cooldown_seconds = config.DEFAULT_COOLDOWN_SECONDS
        self.require_news = config.DEFAULT_REQUIRE_NEWS
        self.feed_tier = "institutional"  # "retail" | "institutional"
        self.mode = "live" if config.live_data_available() else "simulated"

        # Per-tick engine state.
        self._tick = 0
        self._last_price = 80.15
        self._wti_history: list[dict] = []
        self._brent_history: list[dict] = []
        self._volume_history: list[dict] = []
        self._icebergs: list[dict] = []
        self._dark_pool: list[dict] = []
        self._news: list[dict] = []
        self._iceberg_tracker = orderflow.IcebergTracker()
        self._prior_range = PriorSessionRange()

        self._cooldown_until = 0.0
        self._suppressed_count = 0
        self._last_live_fetch = 0.0
        self._live_prices: dict | None = None

        self._thread: threading.Thread | None = None
        self._running = False

    # -- config setters -----------------------------------------------------
    def update_config(self, *, z_threshold=None, cooldown_seconds=None, require_news=None, feed_tier=None, mode=None):
        if z_threshold is not None:
            self.z_threshold = float(z_threshold)
        if cooldown_seconds is not None:
            self.cooldown_seconds = int(cooldown_seconds)
        if require_news is not None:
            self.require_news = bool(require_news)
        if feed_tier in ("retail", "institutional"):
            self.feed_tier = feed_tier
        if mode in ("live", "simulated"):
            # Only honour "live" if data is actually available.
            self.mode = "live" if (mode == "live" and config.live_data_available()) else "simulated"
        return self.current_config()

    def current_config(self) -> dict:
        return {
            "z_threshold": self.z_threshold,
            "cooldown_seconds": self.cooldown_seconds,
            "require_news": self.require_news,
            "feed_tier": self.feed_tier,
            "mode": self.mode,
            "live_available": config.live_data_available(),
            "channels": config.channel_availability(),
            "providers": config.provider_availability(),
        }

    # -- lifecycle ----------------------------------------------------------
    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, name="tick-loop", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False

    def _refresh_seconds(self) -> int:
        return config.LIVE_REFRESH_SECONDS if self.mode == "live" else config.REFRESH_SECONDS

    def _loop(self) -> None:
        # Produce an initial snapshot immediately so pages don't wait a full
        # refresh interval for their first paint.
        self.holder.set(self.tick())
        while self._running:
            time.sleep(self._refresh_seconds())
            try:
                self.holder.set(self.tick())
            except Exception:
                # Never let a bad tick kill the loop.
                continue

    # -- live data ----------------------------------------------------------
    def _maybe_fetch_live(self) -> None:
        if self.mode != "live":
            return
        now = time.time()
        if now - self._last_live_fetch < self._refresh_seconds():
            return
        self._last_live_fetch = now
        try:
            from engine.data_providers import yfinance_provider, news_provider

            prices = yfinance_provider.fetch_prices()
            if prices:
                self._live_prices = prices
            headlines = news_provider.fetch_headlines()
            if headlines:
                self._news = headlines[:25]
        except Exception:
            pass

    # -- the tick -----------------------------------------------------------
    def tick(self) -> dict:
        """Compute and return the next unified snapshot (§3)."""
        self._tick += 1
        tick = self._tick
        session = session_for_time()

        if self.mode == "live":
            self._maybe_fetch_live()

        # --- price random walk (retail mode advances price only every 4th tick)
        is_retail_stale = self.feed_tier == "retail" and tick % 4 != 0

        if self.mode == "live" and self._live_prices:
            wti_price = self._live_prices["wti"]
            brent_price = self._live_prices["brent"]
            wti_change = self._live_prices["wti_change"]
            brent_change = self._live_prices["brent_change"]
            self._last_price = wti_price
        else:
            if not is_retail_stale:
                delta = _rand(-0.18, 0.18)
                self._last_price = _clamp(self._last_price + delta, 55, 140)
            wti_price = self._last_price
            brent_price = self._last_price + _rand(3.8, 5.2)
            prev_wti = self._wti_history[-1]["price"] if self._wti_history else wti_price
            prev_brent = self._brent_history[-1]["price"] if self._brent_history else brent_price
            wti_change = wti_price - prev_wti
            brent_change = brent_price - prev_brent

        if not is_retail_stale:
            self._wti_history.append({"t": tick, "price": round(wti_price, 2)})
            self._brent_history.append({"t": tick, "price": round(brent_price, 2)})
            self._wti_history = self._wti_history[-60:]
            self._brent_history = self._brent_history[-60:]

        self._prior_range.update(session["key"], wti_price)

        # --- session-relative volume + spike injection ---
        base = base_volume(session["key"])
        is_spike = random.random() < 0.1
        if self.mode == "live" and self._live_prices and self._live_prices.get("volume"):
            # Real volume, scaled so the same session-relative z-score applies.
            raw = self._live_prices["volume"]
            # Normalise huge exchange volumes into the baseline's neighbourhood.
            volume = base * _clamp(raw / max(raw, 1) + _rand(0.6, 1.4), 0.3, 25)
        else:
            volume = base * _rand(8, 22) if is_spike else base * _rand(0.55, 1.3)
        vol_z = volume_z_score(volume, session["key"])
        self._volume_history.append(
            {"t": tick, "volume": round(volume), "session": session["key"], "z": round(vol_z, 3)}
        )
        self._volume_history = self._volume_history[-60:]

        # --- order flow (ALWAYS simulated) ---
        imbalance = orderflow.simulate_imbalance(is_spike)
        book = orderflow.build_order_book(self._last_price, imbalance)
        confirmed = self._iceberg_tracker.update(tick, self._last_price)
        if confirmed:
            self._icebergs = (confirmed + self._icebergs)[:15]
        block = orderflow.maybe_dark_pool_print(self._last_price)
        if block:
            self._dark_pool = ([block] + self._dark_pool)[:15]

        # --- news (simulated pool, unless live provided real headlines) ---
        news_direction = None
        if self.mode != "live" and random.random() < 0.12:
            headline = random.choice(config.HEADLINE_POOL)
            analysis = analyze_headline(headline)
            item = {
                "time": _now_iso(),
                "source": random.choice(config.WIRE_SOURCES),
                "headline": headline,
                "entities": analysis["entities"],
                "sentiment": analysis["score"],
                "confidence": analysis["confidence"],
                "market_moving": analysis["market_moving"],
            }
            self._news = ([item] + self._news)[:25]
            if analysis["market_moving"]:
                news_direction = "long" if analysis["score"] >= 0 else "short"

        # --- multi-factor alert logic ---
        result = alerts_engine.evaluate_alert(
            volume_z=vol_z,
            imbalance=imbalance,
            z_threshold=self.z_threshold,
            require_news=self.require_news,
            news_direction=news_direction,
        )
        alert_fired = None
        now = time.time()
        if result["conditions_met"]:
            if now < self._cooldown_until:
                self._suppressed_count += 1
            else:
                alert_fired = {
                    "direction": result["direction"],
                    "session": session["key"],
                    "session_label": session["label"],
                    "factors": result["factors"],
                    "vol_z": round(vol_z, 2),
                    "imbalance": round(imbalance, 2),
                    "time": _now_iso(),
                }
                self._cooldown_until = now + self.cooldown_seconds
                if self.store:
                    self.store.record(
                        direction=result["direction"],
                        session=session["label"],
                        vol_z=vol_z,
                        imbalance=imbalance,
                        factors=result["factors"],
                    )

        cooldown_remaining = max(0, int(round(self._cooldown_until - now)))

        latency = "0.4-1.1 ms" if self.feed_tier == "institutional" else "260-900 ms"

        snapshot = {
            "ts": _now_iso(),
            "tick": tick,
            "mode": self.mode,
            "feed_tier": self.feed_tier,
            "latency": latency,
            "session": {"active": session["key"], "label": session["label"]},
            "price": {
                "wti": round(wti_price, 2),
                "brent": round(brent_price, 2),
                "wti_change": round(wti_change, 2),
                "brent_change": round(brent_change, 2),
                "wti_history": self._wti_history,
                "brent_history": self._brent_history,
            },
            "volume": {
                "current": round(volume),
                "baseline_mean": round(base),
                "z_score": round(vol_z, 2),
                "history": self._volume_history,
            },
            "orderflow": {
                "imbalance": round(imbalance, 2),
                "bids": book["bids"],
                "asks": book["asks"],
                "icebergs": self._icebergs,
                "dark_pool_prints": self._dark_pool,
            },
            "news": self._news,
            "loop_score": loop_score(vol_z, imbalance, len(self._news)),
            "alert_fired": alert_fired,
            "config": {
                "z_threshold": self.z_threshold,
                "cooldown_seconds": self.cooldown_seconds,
                "require_news": self.require_news,
            },
            "cooldown_remaining": cooldown_remaining,
            "suppressed_count": self._suppressed_count,
        }
        return snapshot
