"""Non-secret configuration and reference data for Oil Session Radar — Institutional Desk.

Everything in here is safe to commit. Secrets (API keys, SMTP/Twilio/Telegram
credentials) are read from environment variables at runtime — see ``.env.example``.
"""
from __future__ import annotations

import os

# ---------------------------------------------------------------------------
# Runtime toggles / thresholds
# ---------------------------------------------------------------------------

# Seconds between simulation ticks / snapshot refreshes. Fast in simulated demo
# mode; configurable (up to 300s) in live mode to respect free-tier rate limits.
REFRESH_SECONDS = int(os.environ.get("REFRESH_SECONDS", "5"))
LIVE_REFRESH_SECONDS = int(os.environ.get("LIVE_REFRESH_SECONDS", "60"))

# Default multi-factor alert configuration (mutable at runtime via the API).
DEFAULT_Z_THRESHOLD = 2.5
DEFAULT_COOLDOWN_SECONDS = 75
DEFAULT_REQUIRE_NEWS = False

# Order-flow imbalance magnitude that counts as an "order-flow shift".
ORDERFLOW_SHIFT_THRESHOLD = 2.0

# Symbols used for live yfinance pulls and the backtest lab.
WTI_SYMBOL = "CL=F"      # NYMEX WTI crude front-month future
BRENT_SYMBOL = "BZ=F"    # ICE Brent crude front-month future

# ---------------------------------------------------------------------------
# Trading sessions (UTC hour boundaries). Ported from the JSX SESSIONS array.
# ---------------------------------------------------------------------------

SESSIONS = [
    {"key": "asian", "label": "Asian", "start": 0, "end": 8, "color": "#38bdf8"},
    {"key": "london", "label": "London", "start": 8, "end": 13, "color": "#34d399"},
    {"key": "ny", "label": "New York", "start": 13, "end": 21, "color": "#fbbf24"},
    {"key": "off", "label": "Off-hours", "start": 21, "end": 24, "color": "#64748b"},
]

# Per-session baseline volume used for the session-relative z-score.
SESSION_BASE_VOLUME = {"ny": 4200, "london": 3100, "asian": 1800, "off": 900}

# ---------------------------------------------------------------------------
# Data vendors table (overview page). Ported from the JSX DATA_VENDORS array.
# ---------------------------------------------------------------------------

DATA_VENDORS = [
    {"name": "ICE (Brent futures)", "protocol": "FIX 5.0 / co-located", "tier": "enterprise", "connected": False},
    {"name": "CME/NYMEX Globex (WTI)", "protocol": "FIX / MDP 3.0 (ITCH-like)", "tier": "enterprise", "connected": False},
    {"name": "Bloomberg B-PIPE", "protocol": "Proprietary low-latency feed", "tier": "enterprise", "connected": False},
    {"name": "Refinitiv (LSEG) Elektron", "protocol": "Elektron Direct WebSocket", "tier": "enterprise", "connected": False},
    {"name": "dxFeed", "protocol": "dxLink WebSocket", "tier": "enterprise", "connected": False},
]

# ---------------------------------------------------------------------------
# Historical break events (backtest page). Ported from the JSX HISTORICAL_EVENTS.
# ---------------------------------------------------------------------------

HISTORICAL_EVENTS = [
    {
        "id": "2020-04-20",
        "title": "WTI settles negative",
        "date": "20 Apr 2020",
        "detail": "May-contract WTI settled at -$37.63/bbl as storage capacity ran out during pandemic demand collapse.",
        "move": "-305%",
        "prior_signal": "Extreme volume + repeated failed-bid iceberg clusters into the close",
    },
    {
        "id": "2022-03-08",
        "title": "Brent spikes on Ukraine invasion",
        "date": "Mar 2022",
        "detail": "Brent surged above $127-139/bbl, highest since 2008, on Russia sanctions and supply-security fears.",
        "move": "+9.4% (1d)",
        "prior_signal": "Overnight Asian-session volume z-score >4, news wire confirmation within 90s",
    },
    {
        "id": "2022-03-31",
        "title": "Record U.S. SPR release announced",
        "date": "31 Mar 2022",
        "detail": "White House announced release of ~1 mb/d for 180 days (~180M bbl total) from the Strategic Petroleum Reserve.",
        "move": "-4.9% (1d)",
        "prior_signal": "Pre-announcement order-flow imbalance shifted short 40 min ahead of the wire hit",
    },
    {
        "id": "2026-02-28",
        "title": "Iran-U.S. war outbreak / Hormuz disruption",
        "date": "28 Feb 2026 - present",
        "detail": "IEA called it the largest oil-supply disruption on record; Brent peaked near $126 intraday (30 Apr 2026).",
        "move": "+75% (peak vs pre-war)",
        "prior_signal": "Sustained multi-session volume anomaly + persistent bid-side imbalance across Asian/London opens",
    },
]

# ---------------------------------------------------------------------------
# Latency budget waterfall (infrastructure page). Ported from the JSX version.
# ---------------------------------------------------------------------------

LATENCY_BUDGET = [
    {"hop": "Exchange match engine -> co-lo NIC", "ms": 0.3},
    {"hop": "FIX/WS feed handler parse", "ms": 0.4},
    {"hop": "Kafka produce + replicate", "ms": 1.2},
    {"hop": "Flink windowed calc (z-score/imbalance)", "ms": 8.5},
    {"hop": "Redis state read/write", "ms": 0.6},
    {"hop": "Alert dispatch (email/SMS/Telegram API)", "ms": 240.0},
]

PIPELINE_STAGES = [
    "Exchange\n(ICE / CME)",
    "Co-located\nfeed handler",
    "Kafka\ningest topic",
    "Flink\nstream job",
    "Redis\nin-memory state",
    "Alert\ndispatcher",
]

# ---------------------------------------------------------------------------
# Reference knowledge base (reference page).
# Ported from the earlier Streamlit project's config.py.
# ---------------------------------------------------------------------------

TRADING_HOUSES = [
    {"name": "Vitol", "hq": "Geneva / Rotterdam", "note": "World's largest independent energy trader by volume."},
    {"name": "Trafigura", "hq": "Singapore / Geneva", "note": "Major crude & refined products trader; large logistics arm."},
    {"name": "Glencore", "hq": "Baar, Switzerland", "note": "Diversified commodities; significant crude and products book."},
    {"name": "Gunvor", "hq": "Geneva / Singapore", "note": "Crude, products and LNG; strong Atlantic-basin presence."},
    {"name": "Mercuria", "hq": "Geneva", "note": "Energy-focused trader with growing renewables desk."},
    {"name": "Unipec / Sinopec", "hq": "Beijing / Singapore", "note": "Trading arm of Sinopec; anchors Chinese crude demand."},
    {"name": "Saudi Aramco", "hq": "Dhahran", "note": "Largest crude producer; sets official selling prices (OSPs)."},
]

MAJOR_PORTS = [
    {"name": "Rotterdam", "country": "Netherlands", "role": "Europe's largest oil hub / ARA storage complex."},
    {"name": "Singapore", "country": "Singapore", "role": "Asia's refining & bunkering hub; Malacca gateway."},
    {"name": "Shanghai", "country": "China", "role": "Key Chinese import/refining gateway."},
    {"name": "Jebel Ali", "country": "UAE", "role": "Largest Middle East port; Gulf export logistics."},
    {"name": "Houston", "country": "USA", "role": "U.S. Gulf Coast crude & products export center."},
    {"name": "Fujairah", "country": "UAE", "role": "Bunkering & storage hub just outside the Strait of Hormuz."},
]

CHOKEPOINTS = [
    {"name": "Strait of Hormuz", "flow": "~20 mb/d", "note": "The single most important oil chokepoint; Gulf exports."},
    {"name": "Strait of Malacca", "flow": "~16 mb/d", "note": "Links Indian Ocean to the South China Sea / East Asia."},
    {"name": "Suez Canal", "flow": "~5-6 mb/d", "note": "Red Sea <-> Mediterranean shortcut; SUMED pipeline parallel."},
    {"name": "Panama Canal", "flow": "~0.9 mb/d", "note": "Atlantic <-> Pacific; draft limits constrain tankers."},
    {"name": "English Channel", "flow": "high traffic", "note": "Busiest shipping lane; feeds NW Europe refining."},
]

# ---------------------------------------------------------------------------
# NLP dictionaries. Ported verbatim from the JSX prototype.
# ---------------------------------------------------------------------------

ENTITY_DICTIONARY = {
    "OPEC+": ["opec+", "opec", "output cut", "production cut", "quota"],
    "Strait of Hormuz": ["hormuz"],
    "Strategic Petroleum Reserve": ["spr", "strategic petroleum reserve", "strategic reserve"],
    "Strait of Malacca": ["malacca"],
    "Suez Canal": ["suez"],
    "Refinery": ["refinery", "refining capacity", "turnaround"],
    "U.S. Federal Reserve": ["federal reserve", "fed ", "rate decision", "fomc"],
    "China demand": ["china", "chinese demand", "beijing"],
}

BULLISH_WORDS = [
    "cut", "outage", "disruption", "blockade", "attack", "halt", "shortage",
    "draw", "sanctions", "closure", "strike", "seized",
]
BEARISH_WORDS = [
    "increase", "boost", "release", "surplus", "oversupply", "ceasefire",
    "resume", "build", "glut", "resumes", "reopen", "truce",
]

HEADLINE_POOL = [
    "OPEC+ delegates said to weigh deeper output cut at next month's meeting",
    "Tanker traffic through the Strait of Hormuz drops sharply amid naval buildup",
    "White House weighs new Strategic Petroleum Reserve release to cool prices",
    "Refinery outage reported on U.S. Gulf Coast after unplanned unit shutdown",
    "China demand data beats expectations as refiners lift crude throughput",
    "Fed officials signal rate decision could hinge on energy-driven inflation",
    "Reports of blockade near Strait of Malacca disrupt regional freight rates",
    "OPEC+ agrees to hold quotas steady, citing balanced market conditions",
    "Ceasefire talks resume, easing fears of prolonged Hormuz shipping disruption",
    "Suez Canal Authority reports normal transit volumes after brief closure scare",
    "Sanctions tighten on crude exports, tightening seaborne supply further",
    "Surplus fears build as non-OPEC supply growth outpaces demand forecasts",
    "Strike halts loading operations at major North Sea export terminal",
    "SPR release announced: barrels to hit market over the coming weeks",
]

WIRE_SOURCES = ["Dow Jones Newswires", "Reuters", "Bloomberg"]


# ---------------------------------------------------------------------------
# Secret / credential availability helpers (never expose values, only presence)
# ---------------------------------------------------------------------------

def _has(*keys: str) -> bool:
    return all(os.environ.get(k) for k in keys)


def live_data_available() -> bool:
    """Live mode auto-enables when at least a news key or EIA/Alpha key is set.

    Price/volume via yfinance needs no key, so any of these unlocks richer live
    data. yfinance alone still upgrades price/volume even with no keys, but we
    keep the default demo mode unless the user explicitly opts in or configures
    a key, matching the .env-driven pattern from the Streamlit project.
    """
    return _has("NEWSAPI_API_KEY") or _has("EIA_API_KEY") or _has("ALPHA_VANTAGE_API_KEY")


def channel_availability() -> dict:
    """Which alert channels are configured (presence of required env keys)."""
    return {
        "email": _has("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "ALERT_EMAIL_TO"),
        "sms": _has("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_FROM", "TWILIO_TO"),
        "telegram": _has("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"),
    }


def provider_availability() -> dict:
    return {
        "yfinance": True,  # no key required
        "newsapi": _has("NEWSAPI_API_KEY"),
        "eia": _has("EIA_API_KEY"),
        "alpha_vantage": _has("ALPHA_VANTAGE_API_KEY"),
    }
