"""Historical calibration engine — real backtest over yfinance history.

Unlike the JSX prototype (which could only show illustrative placeholder
numbers), this runs real Python over real historical data. It pulls intraday
OHLCV, tags each bar to a UTC session, flags session-relative volume anomalies,
and reports the true per-session average *signed forward return* and *win rate*.
Same methodology as the earlier Streamlit project's ``src/analytics/backtest.py``.

If yfinance is unavailable or returns no data (offline / rate-limited), the
runner returns ``available: False`` and the UI keeps the illustrative table
clearly labelled as illustrative — it never silently fakes real numbers.
"""
from __future__ import annotations

from engine.sessions import session_for_hour


def run_backtest(
    symbol: str,
    period: str = "60d",
    interval: str = "1h",
    z_threshold: float = 2.5,
    forward_bars: int = 1,
) -> dict:
    """Return real per-session signal stats for ``symbol`` over ``period``.

    Result shape::

        {
          "available": bool,
          "symbol": ..., "period": ..., "interval": ...,
          "bars": <int>,
          "sessions": [
            {"session": "New York", "alerts": 12, "followed_move": 8,
             "false_alarms": 4, "win_rate": "66.7%", "avg_fwd_return": "0.41%"},
            ...
          ],
          "error": <str, only when available is False>
        }
    """
    try:
        import yfinance as yf
    except Exception as exc:  # pragma: no cover - import guard
        return {"available": False, "error": f"yfinance not installed: {exc}", "symbol": symbol}

    try:
        df = yf.download(
            symbol, period=period, interval=interval, progress=False, auto_adjust=False
        )
    except Exception as exc:
        return {"available": False, "error": f"download failed: {exc}", "symbol": symbol}

    if df is None or df.empty:
        return {"available": False, "error": "no data returned", "symbol": symbol}

    # Normalise columns (yfinance may return a MultiIndex for single tickers).
    if hasattr(df.columns, "nlevels") and df.columns.nlevels > 1:
        df.columns = df.columns.get_level_values(0)

    closes = df["Close"].tolist()
    volumes = df["Volume"].tolist()
    index = df.index.tolist()
    n = len(closes)

    # Aggregate per session.
    agg: dict[str, dict] = {}
    move_threshold = 0.01  # 1% forward move counts as "followed"

    for i in range(n - forward_bars):
        ts = index[i]
        hour = ts.hour if hasattr(ts, "hour") else 0
        session = session_for_hour(hour)
        key = session["label"]

        vol = float(volumes[i]) if volumes[i] == volumes[i] else 0.0  # NaN guard
        # Scale real exchange volume onto the session baseline space so the
        # same session-relative z-score definition applies. We compare each
        # bar's volume to that session's own mean within this dataset.
        bucket = agg.setdefault(
            key, {"vols": [], "idxs": [], "alerts": 0, "followed": 0, "fwd_returns": []}
        )
        bucket["vols"].append(vol)
        bucket["idxs"].append(i)

    for key, bucket in agg.items():
        vols = bucket["vols"]
        if not vols:
            continue
        mean_v = sum(vols) / len(vols)
        std_v = (sum((v - mean_v) ** 2 for v in vols) / len(vols)) ** 0.5 or 1.0
        for pos, i in enumerate(bucket["idxs"]):
            z = (vols[pos] - mean_v) / std_v
            if z >= z_threshold:
                bucket["alerts"] += 1
                c0 = closes[i]
                c1 = closes[i + forward_bars]
                if c0:
                    fwd = (c1 - c0) / c0
                    bucket["fwd_returns"].append(fwd)
                    if abs(fwd) >= move_threshold:
                        bucket["followed"] += 1

    sessions_out = []
    for key in ["Asian", "London", "New York", "Off-hours"]:
        if key not in agg:
            continue
        b = agg[key]
        alerts = b["alerts"]
        followed = b["followed"]
        false_alarms = alerts - followed
        win_rate = (followed / alerts * 100) if alerts else 0.0
        avg_fwd = (sum(b["fwd_returns"]) / len(b["fwd_returns"]) * 100) if b["fwd_returns"] else 0.0
        sessions_out.append(
            {
                "session": key,
                "alerts": alerts,
                "followed_move": followed,
                "false_alarms": false_alarms,
                "win_rate": f"{win_rate:.1f}%",
                "avg_fwd_return": f"{avg_fwd:+.2f}%",
            }
        )

    return {
        "available": True,
        "symbol": symbol,
        "period": period,
        "interval": interval,
        "z_threshold": z_threshold,
        "bars": n,
        "sessions": sessions_out,
    }
