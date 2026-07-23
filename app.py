"""Flask app factory. Registers blueprints and starts the background tick thread.

Run locally with ``python app.py`` (dev server) or ``flask --app app run --debug``.
In containers, run with ``gunicorn`` — see the Dockerfile and README §Deployment.
"""
from __future__ import annotations

import os

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # python-dotenv optional at runtime
    pass

from flask import Flask

from engine.simulation import MarketSimulation
from routes.api import api_bp
from routes.stream import stream_bp
from routes.views import views_bp
from storage.signal_store import SignalStore


def create_app() -> Flask:
    app = Flask(__name__, static_folder="static", template_folder="templates")

    store = SignalStore()
    sim = MarketSimulation(store=store)

    app.config["SIM"] = sim
    app.config["STORE"] = store

    app.register_blueprint(views_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(stream_bp)

    # Start the single background tick loop once. Guard against the Flask
    # reloader starting it twice in debug mode.
    if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        sim.start()

    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "7860"))
    # threaded=True lets the long-lived /stream connection coexist with normal
    # request handling on the dev server.
    app.run(host="0.0.0.0", port=port, threaded=True, debug=False)
