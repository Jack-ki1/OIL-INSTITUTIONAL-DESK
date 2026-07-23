"""Real live WTI/Brent price + volume via yfinance. No API key required.

Server-side calls only (no CORS, no client-exposed key). Returns None on any
failure so callers can fall back to simulated data.
"""
from __future__ import annotations

import config


def _last_two_closes_and_volume(symbol: str):
    import yfinance as yf

    df = yf.download(symbol, period="2d", interval="1m", progress=False, auto_adjust=False)
    if df is None or df.empty:
        # fall back to daily bars
        df = yf.download(symbol, period="5d", interval="1d", progress=False, auto_adjust=False)
    if df is None or df.empty:
        return None
    if hasattr(df.columns, "nlevels") and df.columns.nlevels > 1:
        df.columns = df.columns.get_level_values(0)
    closes = df["Close"].dropna().tolist()
    volumes = df["Volume"].dropna().tolist()
    if not closes:
        return None
    price = float(closes[-1])
    change = float(closes[-1] - closes[-2]) if len(closes) > 1 else 0.0
    volume = float(volumes[-1]) if volumes else 0.0
    return price, change, volume


def fetch_prices() -> dict | None:
    """Return {'wti', 'brent', 'wti_change', 'brent_change', 'volume'} or None."""
    try:
        wti = _last_two_closes_and_volume(config.WTI_SYMBOL)
        brent = _last_two_closes_and_volume(config.BRENT_SYMBOL)
        if not wti or not brent:
            return None
        return {
            "wti": round(wti[0], 2),
            "brent": round(brent[0], 2),
            "wti_change": round(wti[1], 2),
            "brent_change": round(brent[1], 2),
            "volume": wti[2],
        }
    except Exception:
        return None
