"""
Agent Heartbeat Monitor — uptime tracking for AI agents.

Agents call POST /heartbeat/{agent_id} on their loop (every 60s typical).
We track uptime, streak, and last_seen. Any agent silent > threshold = "dead".
Free: 1 agent per registration, no limits.

Endpoints:
  POST /heartbeat/{agent_id}          — send heartbeat (must be registered)
  GET  /heartbeat/{agent_id}/status   — alive/degraded/dead + uptime stats
  GET  /stats/heartbeat               — platform-wide uptime stats
"""

import sqlite3
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "heartbeat.db"
DB_PATH.parent.mkdir(exist_ok=True)

_local = threading.local()

# Agent is "dead" if no heartbeat for this many seconds
DEAD_THRESHOLD = 300   # 5 minutes
DEGRADED_THRESHOLD = 120  # 2 minutes


def _get_conn() -> sqlite3.Connection:
    if not hasattr(_local, "conn"):
        _local.conn = sqlite3.connect(str(DB_PATH), timeout=10)
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _local.conn.execute("""
            CREATE TABLE IF NOT EXISTS heartbeats (
                agent_id TEXT PRIMARY KEY,
                first_beat REAL NOT NULL,
                last_beat REAL NOT NULL,
                total_beats INTEGER DEFAULT 1,
                uptime_streak INTEGER DEFAULT 1,
                longest_streak INTEGER DEFAULT 1
            )
        """)
        _local.conn.commit()
    return _local.conn


def record_heartbeat(agent_id: str) -> dict:
    conn = _get_conn()
    now = time.time()

    row = conn.execute(
        "SELECT first_beat, last_beat, total_beats, uptime_streak, longest_streak FROM heartbeats WHERE agent_id=?",
        (agent_id,),
    ).fetchone()

    if row is None:
        conn.execute(
            "INSERT INTO heartbeats (agent_id, first_beat, last_beat, total_beats, uptime_streak, longest_streak) VALUES (?,?,?,1,1,1)",
            (agent_id, now, now),
        )
        conn.commit()
        return {
            "status": "alive",
            "total_beats": 1,
            "uptime_streak": 1,
            "message": "First heartbeat recorded. Agent is monitored.",
        }

    first_beat, last_beat, total_beats, streak, longest = row
    gap = now - last_beat

    # If gap > DEAD_THRESHOLD, streak resets
    if gap > DEAD_THRESHOLD:
        new_streak = 1
    else:
        new_streak = streak + 1

    new_longest = max(longest, new_streak)
    new_total = total_beats + 1

    conn.execute(
        "UPDATE heartbeats SET last_beat=?, total_beats=?, uptime_streak=?, longest_streak=? WHERE agent_id=?",
        (now, new_total, new_streak, new_longest, agent_id),
    )
    conn.commit()

    uptime_seconds = now - first_beat
    uptime_pct = round((new_total * 60) / uptime_seconds * 100, 1) if uptime_seconds > 60 else 100.0

    return {
        "status": "alive",
        "total_beats": new_total,
        "uptime_streak": new_streak,
        "longest_streak": new_longest,
        "uptime_pct_estimate": min(uptime_pct, 100.0),
        "last_gap_seconds": round(gap, 1),
    }


def get_status(agent_id: str) -> dict | None:
    conn = _get_conn()
    row = conn.execute(
        "SELECT first_beat, last_beat, total_beats, uptime_streak, longest_streak FROM heartbeats WHERE agent_id=?",
        (agent_id,),
    ).fetchone()

    if row is None:
        return None

    first_beat, last_beat, total_beats, streak, longest = row
    now = time.time()
    seconds_since = now - last_beat

    if seconds_since < DEGRADED_THRESHOLD:
        status = "alive"
    elif seconds_since < DEAD_THRESHOLD:
        status = "degraded"
    else:
        status = "dead"

    uptime_seconds = now - first_beat
    uptime_pct = round((total_beats * 60) / uptime_seconds * 100, 1) if uptime_seconds > 60 else 100.0

    return {
        "agent_id": agent_id,
        "status": status,
        "last_beat": datetime.fromtimestamp(last_beat, tz=timezone.utc).isoformat(),
        "seconds_since_last_beat": round(seconds_since, 1),
        "total_beats": total_beats,
        "uptime_streak": streak,
        "longest_streak": longest,
        "uptime_pct_estimate": min(uptime_pct, 100.0),
        "monitoring_since": datetime.fromtimestamp(first_beat, tz=timezone.utc).isoformat(),
        "thresholds": {
            "degraded_after_seconds": DEGRADED_THRESHOLD,
            "dead_after_seconds": DEAD_THRESHOLD,
        },
    }


def heartbeat_platform_stats() -> dict:
    conn = _get_conn()
    now = time.time()

    total = conn.execute("SELECT COUNT(*) FROM heartbeats").fetchone()[0]
    alive = conn.execute(
        "SELECT COUNT(*) FROM heartbeats WHERE last_beat > ?", (now - DEGRADED_THRESHOLD,)
    ).fetchone()[0]
    degraded = conn.execute(
        "SELECT COUNT(*) FROM heartbeats WHERE last_beat > ? AND last_beat <= ?",
        (now - DEAD_THRESHOLD, now - DEGRADED_THRESHOLD),
    ).fetchone()[0]
    dead = total - alive - degraded

    return {
        "monitored_agents": total,
        "alive": alive,
        "degraded": degraded,
        "dead": dead,
        "thresholds": {
            "degraded_after_seconds": DEGRADED_THRESHOLD,
            "dead_after_seconds": DEAD_THRESHOLD,
        },
        "note": "Agents call POST /heartbeat/{agent_id} to stay alive. Free.",
    }
