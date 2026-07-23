"""Optional Alpha Vantage cross-check for official WTI/Brent spot prices.

Only used when ``ALPHA_VANTAGE_API_KEY`` is set. Returns None otherwise.
"""
from __future__ import annotations

import os


def fetch_reference_prices() -> dict | None:
    key = os.environ.get("ALPHA_VANTAGE_API_KEY")
    if not key:
        return None
    try:
        import requests

        out: dict[str, float] = {}
        for label, fn in (("wti", "WTI"), ("brent", "BRENT")):
            resp = requests.get(
                "https://www.alphavantage.co/query",
                params={"function": fn, "interval": "daily", "apikey": key},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json().get("data") or []
            if data:
                out[label] = float(data[0]["value"])
        return out or None
    except Exception:
        return None
