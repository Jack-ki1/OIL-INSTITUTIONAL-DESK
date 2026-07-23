"""GET /stream — the Server-Sent Events endpoint.

Streams the latest unified snapshot as ``data: {json}\\n\\n`` events. The
background tick loop is the producer; this endpoint just fans the current
snapshot out to each connected client, sleeping briefly between reads.
"""
from __future__ import annotations

import json
import time

from flask import Blueprint, Response, current_app

stream_bp = Blueprint("stream", __name__)


@stream_bp.route("/stream")
def stream():
    sim = current_app.config["SIM"]

    def generate():
        last_tick = None
        # Emit an initial retry hint so EventSource reconnects promptly.
        yield "retry: 3000\n\n"
        while True:
            snapshot = sim.holder.get()
            if snapshot is not None and snapshot.get("tick") != last_tick:
                last_tick = snapshot.get("tick")
                yield f"data: {json.dumps(snapshot)}\n\n"
            else:
                # keep-alive comment so proxies don't drop an idle connection
                yield ": keep-alive\n\n"
            time.sleep(1)

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
