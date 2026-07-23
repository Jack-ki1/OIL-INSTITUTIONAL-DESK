"""Optional U.S. EIA open-data reference prices (spot WTI Cushing / Brent Europe).

Only used when ``EIA_API_KEY`` is set. Returns None otherwise.
"""
from __future__ import annotations

import os

# EIA v2 series IDs for daily spot prices.
_WTI_SERIES = "PET.RWTC.D"
_BRENT_SERIES = "PET.RBRTE.D"


def _fetch_series(series_id: str, key: str):
    import requests

    resp = requests.get(
        f"https://api.eia.gov/v2/seriesid/{series_id}",
        params={"api_key": key},
        timeout=15,
    )
    resp.raise_for_status()
    rows = resp.json().get("response", {}).get("data", [])
    if rows:
        return float(rows[0]["value"])
    return None


def fetch_reference_prices() -> dict | None:
    key = os.environ.get("EIA_API_KEY")
    if not key:
        return None
    try:
        out: dict[str, float] = {}
        wti = _fetch_series(_WTI_SERIES, key)
        brent = _fetch_series(_BRENT_SERIES, key)
        if wti is not None:
            out["wti"] = wti
        if brent is not None:
            out["brent"] = brent
        return out or None
    except Exception:
        return None
