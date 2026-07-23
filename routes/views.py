"""GET routes that render Jinja2 templates."""
from __future__ import annotations

from flask import Blueprint, current_app, render_template

import config

views_bp = Blueprint("views", __name__)


def _sim():
    return current_app.config["SIM"]


def _common():
    sim = _sim()
    return {
        "cfg": sim.current_config(),
        "sessions": config.SESSIONS,
        "banner": (
            "All simulated panels are marked SIM. Live-mode panels use real "
            "market/news data — see README for exact sourcing and rate limits."
        ),
    }


@views_bp.route("/")
def overview():
    return render_template(
        "overview.html", page="overview", data_vendors=config.DATA_VENDORS, **_common()
    )


@views_bp.route("/orderflow")
def orderflow():
    return render_template("orderflow.html", page="orderflow", **_common())


@views_bp.route("/news")
def news():
    return render_template("news.html", page="news", **_common())


@views_bp.route("/alerts")
def alerts():
    return render_template("alerts.html", page="alerts", **_common())


@views_bp.route("/backtest")
def backtest():
    return render_template(
        "backtest.html",
        page="backtest",
        historical_events=config.HISTORICAL_EVENTS,
        wti_symbol=config.WTI_SYMBOL,
        brent_symbol=config.BRENT_SYMBOL,
        **_common(),
    )


@views_bp.route("/infrastructure")
def infrastructure():
    return render_template(
        "infrastructure.html",
        page="infrastructure",
        pipeline_stages=config.PIPELINE_STAGES,
        latency_budget=config.LATENCY_BUDGET,
        latency_total=round(sum(h["ms"] for h in config.LATENCY_BUDGET), 2),
        **_common(),
    )


@views_bp.route("/reference")
def reference():
    eia_prices = None
    alpha_prices = None
    providers = config.provider_availability()
    if providers["eia"]:
        try:
            from engine.data_providers import eia_provider

            eia_prices = eia_provider.fetch_reference_prices()
        except Exception:
            eia_prices = None
    if providers["alpha_vantage"]:
        try:
            from engine.data_providers import alpha_vantage_provider

            alpha_prices = alpha_vantage_provider.fetch_reference_prices()
        except Exception:
            alpha_prices = None
    return render_template(
        "reference.html",
        page="reference",
        trading_houses=config.TRADING_HOUSES,
        major_ports=config.MAJOR_PORTS,
        chokepoints=config.CHOKEPOINTS,
        eia_prices=eia_prices,
        alpha_prices=alpha_prices,
        **_common(),
    )
