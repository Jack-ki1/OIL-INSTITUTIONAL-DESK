"""SQLite signal log + dedup. Uses only stdlib ``sqlite3``.

Every fired alert is persisted here (with its contributing factors as JSON) so
the Alert Center table survives page reloads and the standalone
``background_monitor.py`` daemon writes to the same DB.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
from datetime import datetime, timezone

_DEFAULT_DB = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "signals.db")


class SignalStore:
    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path or _DEFAULT_DB
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._lock = threading.Lock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    session TEXT NOT NULL,
                    vol_z REAL NOT NULL,
                    imbalance REAL NOT NULL,
                    factors TEXT NOT NULL,
                    dedup_key TEXT UNIQUE
                )
                """
            )

    def record(
        self,
        *,
        direction: str,
        session: str,
        vol_z: float,
        imbalance: float,
        factors: list[dict],
        ts: str | None = None,
    ) -> bool:
        """Insert an alert. Returns True if inserted, False if a dedup collision.

        Dedup key = direction+session+rounded-time-bucket, so the same signal
        logged twice within the same second (e.g. web app + daemon) is stored
        once.
        """
        ts = ts or datetime.now(timezone.utc).isoformat()
        dedup_key = f"{direction}:{session}:{ts[:19]}"
        try:
            with self._lock, self._connect() as conn:
                conn.execute(
                    """INSERT INTO signals (ts, direction, session, vol_z, imbalance, factors, dedup_key)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (ts, direction, session, float(vol_z), float(imbalance), json.dumps(factors), dedup_key),
                )
            return True
        except sqlite3.IntegrityError:
            return False

    def recent(self, limit: int = 40) -> list[dict]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM signals ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        out = []
        for r in rows:
            out.append(
                {
                    "id": r["id"],
                    "ts": r["ts"],
                    "direction": r["direction"],
                    "session": r["session"],
                    "vol_z": r["vol_z"],
                    "imbalance": r["imbalance"],
                    "factors": json.loads(r["factors"]),
                }
            )
        return out

    def count(self) -> int:
        with self._lock, self._connect() as conn:
            return conn.execute("SELECT COUNT(*) FROM signals").fetchone()[0]
