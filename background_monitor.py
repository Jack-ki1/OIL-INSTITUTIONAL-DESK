"""Optional standalone always-on alert daemon.

Runs the SAME detection logic as the Flask tick loop on a plain
``while True`` + ``sleep()`` loop — no browser tab or web server required — and
logs fired alerts to the same ``data/signals.db``. Dispatches to whatever alert
channels are configured in the environment (email / SMS / Telegram), failing
soft per channel.

Usage:
    python background_monitor.py

Caveat (same as the earlier Streamlit project): this is for local / your-own-
server use. A container platform's free tier may not keep a detached background
process alive across sleeps/restarts.
"""
from __future__ import annotations

import time

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

import config
from engine import alerts as alerts_engine
from engine.simulation import MarketSimulation
from storage.signal_store import SignalStore


def main() -> None:
    store = SignalStore()
    sim = MarketSimulation(store=store)
    interval = config.REFRESH_SECONDS if sim.mode == "simulated" else config.LIVE_REFRESH_SECONDS

    print(f"[background_monitor] starting in {sim.mode} mode, tick every {interval}s")
    print(f"[background_monitor] channels available: {config.channel_availability()}")

    while True:
        snapshot = sim.tick()
        fired = snapshot.get("alert_fired")
        if fired:
            subject = f"Oil Session Radar alert — {fired['direction'].upper()} ({fired['session_label']})"
            body = (
                f"{fired['direction'].upper()} signal in the {fired['session_label']} session.\n"
                f"Volume z-score: {fired['vol_z']}  |  Imbalance: {fired['imbalance']}\n"
                f"Factors: {fired['factors']}\n"
                f"Time: {fired['time']}"
            )
            results = alerts_engine.dispatch_alert(subject, body)
            print(f"[background_monitor] ALERT fired -> dispatch results: {results}")
        time.sleep(interval)


if __name__ == "__main__":
    main()
