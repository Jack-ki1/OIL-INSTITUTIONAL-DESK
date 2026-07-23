"""Real NewsAPI headlines, run through the SAME news_nlp functions as the
simulated pool. Only the *source* of the headline differs between modes.

Only used when ``NEWSAPI_API_KEY`` is set. Returns [] otherwise.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

from engine.news_nlp import analyze_headline

_QUERY = "crude oil OR OPEC OR Brent OR WTI OR Hormuz"


def fetch_headlines(page_size: int = 15) -> list[dict]:
    key = os.environ.get("NEWSAPI_API_KEY")
    if not key:
        return []
    try:
        import requests

        resp = requests.get(
            "https://newsapi.org/v2/everything",
            params={
                "q": _QUERY,
                "language": "en",
                "sortBy": "publishedAt",
                "pageSize": page_size,
                "apiKey": key,
            },
            timeout=15,
        )
        resp.raise_for_status()
        articles = resp.json().get("articles", [])
        out = []
        for a in articles:
            headline = a.get("title") or ""
            if not headline:
                continue
            analysis = analyze_headline(headline)
            out.append(
                {
                    "time": a.get("publishedAt") or datetime.now(timezone.utc).isoformat(),
                    "source": (a.get("source") or {}).get("name", "NewsAPI"),
                    "headline": headline,
                    "entities": analysis["entities"],
                    "sentiment": analysis["score"],
                    "confidence": analysis["confidence"],
                    "market_moving": analysis["market_moving"],
                }
            )
        return out
    except Exception:
        return []
