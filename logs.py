"""
Agent Logs / Audit Trail — immutable activity log for AI agents.

Agents append what they did and why. Free up to 100 entries/day per agent.
Gives developers a full audit trail of their agent's decisions and actions.
"""

import json
import sqlite3
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).parent / "data" / "logs.db"
DB_PATH.parent.mkdir(exist_ok=True)

FREE_TIER_DAILY = 100

_local = threading.local()


def _get_conn() -> sqlite3.Connection:
    if not hasattr(_local, "conn"):
        _local.conn = sqlite3.connect(str(DB_PATH), timeout=10)
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _local.conn.execute("""
            CREATE TABLE IF NOT EXISTS agent_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                action TEXT NOT NULL,
                result TEXT DEFAULT '',
                metadata TEXT DEFAULT '{}',
                ts REAL NOT NULL,
                day TEXT NOT NULL
            )
        """)
        _local.conn.execute("CREATE INDEX IF NOT EXISTS idx_agent ON agent_logs(agent_id, day)")
        _local.conn.execute("CREATE INDEX IF NOT EXISTS idx_ts ON agent_logs(ts)")
        _local.conn.commit()
    return _local.conn


def _today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def log_append(agent_id: str, action: str, result: str = "", metadata: dict = None) -> dict:
    """Append a log entry for an agent. Returns entry with daily usage."""
    conn = _get_conn()
    today = _today_utc()
    now = time.time()

    # Check daily count
    row = conn.execute(
        "SELECT COUNT(*) FROM agent_logs WHERE agent_id=? AND day=?",
        (agent_id, today),
    ).fetchone()
    daily_count = row[0] if row else 0

    if daily_count >= FREE_TIER_DAILY:
        return {
            "logged": False,
            "error": "daily_limit_reached",
            "limit": FREE_TIER_DAILY,
            "count_today": daily_count,
            "agent_id": agent_id,
        }

    meta_str = json.dumps(metadata or {})
    cursor = conn.execute(
        "INSERT INTO agent_logs (agent_id, action, result, metadata, ts, day) VALUES (?,?,?,?,?,?)",
        (agent_id, action[:200], result[:500], meta_str, now, today),
    )
    conn.commit()

    return {
        "logged": True,
        "id": cursor.lastrowid,
        "agent_id": agent_id,
        "action": action[:200],
        "result": result[:500],
        "ts": now,
        "count_today": daily_count + 1,
        "remaining_today": FREE_TIER_DAILY - daily_count - 1,
    }


def log_get(agent_id: str, limit: int = 100, action_filter: Optional[str] = None) -> dict:
    """Retrieve recent log entries for an agent."""
    conn = _get_conn()

    if action_filter:
        rows = conn.execute(
            "SELECT id, action, result, metadata, ts FROM agent_logs WHERE agent_id=? AND action=? ORDER BY ts DESC LIMIT ?",
            (agent_id, action_filter, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, action, result, metadata, ts FROM agent_logs WHERE agent_id=? ORDER BY ts DESC LIMIT ?",
            (agent_id, limit),
        ).fetchall()

    entries = []
    for r in rows:
        try:
            meta = json.loads(r[3]) if r[3] else {}
        except Exception:
            meta = {}
        entries.append({
            "id": r[0],
            "action": r[1],
            "result": r[2],
            "metadata": meta,
            "ts": r[4],
        })

    return {
        "agent_id": agent_id,
        "count": len(entries),
        "entries": entries,
    }


def log_agent_stats(agent_id: str) -> dict:
    """Stats for a single agent's log activity."""
    conn = _get_conn()
    today = _today_utc()

    total = conn.execute(
        "SELECT COUNT(*) FROM agent_logs WHERE agent_id=?", (agent_id,)
    ).fetchone()[0]

    today_count = conn.execute(
        "SELECT COUNT(*) FROM agent_logs WHERE agent_id=? AND day=?", (agent_id, today)
    ).fetchone()[0]

    # Most common actions
    rows = conn.execute(
        "SELECT action, COUNT(*) as n FROM agent_logs WHERE agent_id=? GROUP BY action ORDER BY n DESC LIMIT 5",
        (agent_id,),
    ).fetchall()
    top_actions = [{"action": r[0], "count": r[1]} for r in rows]

    # First log date
    first = conn.execute(
        "SELECT MIN(ts) FROM agent_logs WHERE agent_id=?", (agent_id,)
    ).fetchone()[0]

    return {
        "agent_id": agent_id,
        "total_entries": total,
        "today": today_count,
        "remaining_today": max(0, FREE_TIER_DAILY - today_count),
        "free_tier_limit": FREE_TIER_DAILY,
        "first_log_ts": first,
        "top_actions": top_actions,
    }


def logs_global_stats() -> dict:
    """Global stats across all agents."""
    conn = _get_conn()

    row = conn.execute(
        "SELECT COUNT(*), COUNT(DISTINCT agent_id) FROM agent_logs"
    ).fetchone()

    today = _today_utc()
    today_row = conn.execute(
        "SELECT COUNT(*), COUNT(DISTINCT agent_id) FROM agent_logs WHERE day=?", (today,)
    ).fetchone()

    # Most active agents today
    top = conn.execute(
        "SELECT agent_id, COUNT(*) as n FROM agent_logs WHERE day=? GROUP BY agent_id ORDER BY n DESC LIMIT 5",
        (today,),
    ).fetchall()

    return {
        "total_entries": row[0] or 0,
        "total_agents": row[1] or 0,
        "entries_today": today_row[0] or 0,
        "active_agents_today": today_row[1] or 0,
        "top_agents_today": [{"agent_id": r[0], "entries": r[1]} for r in top],
    }
