"""JSON REST endpoints: config changes, test alerts, run backtest, alert log."""
from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

import config
from engine import alerts as alerts_engine
from engine import backtest as backtest_engine

api_bp = Blueprint("api", __name__, url_prefix="/api")


def _sim():
    return current_app.config["SIM"]


def _store():
    return current_app.config["STORE"]


@api_bp.route("/config", methods=["GET"])
def get_config():
    return jsonify(_sim().current_config())


@api_bp.route("/config", methods=["POST"])
def set_config():
    body = request.get_json(silent=True) or {}
    cfg = _sim().update_config(
        z_threshold=body.get("z_threshold"),
        cooldown_seconds=body.get("cooldown_seconds"),
        require_news=body.get("require_news"),
        feed_tier=body.get("feed_tier"),
        mode=body.get("mode"),
    )
    return jsonify(cfg)


@api_bp.route("/alerts", methods=["GET"])
def get_alerts():
    store = _store()
    return jsonify({"alerts": store.recent(limit=40), "count": store.count()})


@api_bp.route("/test-alert", methods=["POST"])
def test_alert():
    body = request.get_json(silent=True) or {}
    channel = body.get("channel")
    if channel not in ("email", "sms", "telegram"):
        return jsonify({"ok": False, "error": "unknown channel"}), 400
    available = config.channel_availability()
    if not available.get(channel):
        return jsonify({"ok": False, "error": f"{channel} not configured", "channel": channel}), 200
    results = alerts_engine.dispatch_alert(
        subject="Oil Session Radar — test alert",
        body="This is a test alert from Oil Session Radar — Institutional Desk.",
        channels=[channel],
    )
    result = results[0] if results else {"ok": False, "error": "no result"}
    return jsonify(result)


@api_bp.route("/backtest", methods=["POST"])
def run_backtest():
    body = request.get_json(silent=True) or {}
    symbol = body.get("symbol", config.WTI_SYMBOL)
    period = body.get("period", "60d")
    interval = body.get("interval", "1h")
    z_threshold = float(body.get("z_threshold", _sim().z_threshold))
    result = backtest_engine.run_backtest(
        symbol, period=period, interval=interval, z_threshold=z_threshold
    )
    return jsonify(result)
