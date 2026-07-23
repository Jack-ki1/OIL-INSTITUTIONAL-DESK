"""Keyword-based entity extraction + sentiment scoring.

A deliberately simple, transparent stand-in for a production financial NLP
model (e.g. FinBERT). The exact same functions run over *both* the simulated
headline pool and real NewsAPI headlines — that's what makes the SIM-vs-real
toggle meaningful: the model is real either way, only the headline source
differs. Dictionaries live in ``config`` and are ported verbatim from the JSX
prototype.
"""
from __future__ import annotations

import config


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def extract_entities(text: str) -> list[str]:
    lower = text.lower()
    return [
        name
        for name, keywords in config.ENTITY_DICTIONARY.items()
        if any(kw in lower for kw in keywords)
    ]


def score_sentiment(text: str) -> float:
    """Bull-hits minus bear-hits, normalized to [-1, 1]. 0 when no hits."""
    lower = text.lower()
    bull = sum(1 for w in config.BULLISH_WORDS if w in lower)
    bear = sum(1 for w in config.BEARISH_WORDS if w in lower)
    total = bull + bear
    if total == 0:
        return 0.0
    return (bull - bear) / total


def analyze_headline(text: str) -> dict:
    """Combine entities + sentiment + a confidence heuristic.

    Mirrors the JSX ``analyzeHeadline``: confidence rises with the number of
    matched sentiment keywords; market-moving requires both entities and a
    nonzero sentiment.
    """
    lower = text.lower()
    entities = extract_entities(text)
    bull = sum(1 for w in config.BULLISH_WORDS if w in lower)
    bear = sum(1 for w in config.BEARISH_WORDS if w in lower)
    total = bull + bear
    score = 0.0 if total == 0 else (bull - bear) / total
    confidence = clamp(0.25 + total * 0.2, 0.0, 0.97)
    analysis = {
        "entities": entities,
        "score": round(score, 4),
        "confidence": round(confidence, 4),
    }
    analysis["market_moving"] = is_market_moving(analysis)
    return analysis


def is_market_moving(analysis: dict) -> bool:
    """Has entities AND nonzero sentiment."""
    return bool(analysis.get("entities")) and analysis.get("score", 0.0) != 0.0
