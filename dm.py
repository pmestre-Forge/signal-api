"""
Agent-to-Agent Direct Messaging — private, persistent DMs between registered agents.

Agents send structured messages to each other. History persists. All free.
Rate limit: 50 DMs sent per agent per day (spam prevention).
"""

import json
import sqlite3
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "dm.db"
DB_PATH.parent.mkdir(exist_ok=True)

FREE_TIER_DAILY = 50  # max DMs sent per agent per day

_local = threading.local()


def _get_conn() -> sqlite3.Connection:
    if not hasattr(_local, "conn"):
        _local.conn = sqlite3.connect(str(DB_PATH), timeout=10)
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _local.conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_agent TEXT NOT NULL,
                to_agent   TEXT NOT NULL,
                message    TEXT NOT NULL,
                data       TEXT DEFAULT '{}',
                ts         REAL NOT NULL,
                day        TEXT NOT NULL,
                read       INTEGER DEFAULT 0
            )
        """)
        _local.conn.execute("CREATE INDEX IF NOT EXISTS idx_to   ON messages(to_agent, ts)")
        _local.conn.execute("CREATE INDEX IF NOT EXISTS idx_from ON messages(from_agent, day)")
        _local.conn.execute("CREATE INDEX IF NOT EXISTS idx_thread ON messages(from_agent, to_agent, ts)")
        _local.conn.commit()
    return _local.conn


def _today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def send_dm(from_agent: str, to_agent: str, message: str, data: dict = None) -> dict:
    """Send a direct message from one agent to another."""
    conn = _get_conn()
    today = _today_utc()
    now = time.time()

    # Rate limit check
    row = conn.execute(
        "SELECT COUNT(*) FROM messages WHERE from_agent=? AND day=?",
        (from_agent, today),
    ).fetchone()
    sent_today = row[0] if row else 0

    if sent_today >= FREE_TIER_DAILY:
        return {
            "sent": False,
            "error": "daily_limit_reached",
            "limit": FREE_TIER_DAILY,
            "sent_today": sent_today,
        }

    data_str = json.dumps(data or {})
    cursor = conn.execute(
        "INSERT INTO messages (from_agent, to_agent, message, data, ts, day) VALUES (?,?,?,?,?,?)",
        (from_agent, to_agent, message[:2000], data_str, now, today),
    )
    conn.commit()

    return {
        "sent": True,
        "id": cursor.lastrowid,
        "from_agent": from_agent,
        "to_agent": to_agent,
        "sent_today": sent_today + 1,
        "limit": FREE_TIER_DAILY,
    }


def get_inbox(agent_id: str, limit: int = 20, after_id: int = 0) -> dict:
    """Get messages received by an agent. Marks them as read."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT id, from_agent, message, data, ts, read FROM messages "
        "WHERE to_agent=? AND id>? ORDER BY ts DESC LIMIT ?",
        (agent_id, after_id, min(limit, 100)),
    ).fetchall()

    messages = []
    unread_ids = []
    for row in rows:
        msg_id, from_agent, message, data_str, ts, read = row
        if not read:
            unread_ids.append(msg_id)
        messages.append({
            "id": msg_id,
            "from_agent": from_agent,
            "message": message,
            "data": json.loads(data_str),
            "ts": ts,
            "read": bool(read),
        })

    # Mark unread as read
    if unread_ids:
        conn.execute(
            f"UPDATE messages SET read=1 WHERE id IN ({','.join('?' * len(unread_ids))})",
            unread_ids,
        )
        conn.commit()

    total = conn.execute(
        "SELECT COUNT(*) FROM messages WHERE to_agent=?", (agent_id,)
    ).fetchone()[0]
    unread_total = conn.execute(
        "SELECT COUNT(*) FROM messages WHERE to_agent=? AND read=0", (agent_id,)
    ).fetchone()[0]

    return {
        "agent_id": agent_id,
        "messages": messages,
        "total": total,
        "unread_before_read": len(unread_ids),
        "unread_remaining": unread_total,
    }


def get_thread(agent_a: str, agent_b: str, limit: int = 50) -> dict:
    """Get the full conversation thread between two agents."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT id, from_agent, to_agent, message, data, ts, read FROM messages "
        "WHERE (from_agent=? AND to_agent=?) OR (from_agent=? AND to_agent=?) "
        "ORDER BY ts ASC LIMIT ?",
        (agent_a, agent_b, agent_b, agent_a, min(limit, 200)),
    ).fetchall()

    messages = []
    for row in rows:
        msg_id, from_agent, to_agent, message, data_str, ts, read = row
        messages.append({
            "id": msg_id,
            "from_agent": from_agent,
            "to_agent": to_agent,
            "message": message,
            "data": json.loads(data_str),
            "ts": ts,
            "read": bool(read),
        })

    return {
        "agent_a": agent_a,
        "agent_b": agent_b,
        "message_count": len(messages),
        "messages": messages,
    }


def dm_global_stats() -> dict:
    """Global DM stats."""
    conn = _get_conn()
    total = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
    agents_sending = conn.execute("SELECT COUNT(DISTINCT from_agent) FROM messages").fetchone()[0]
    agents_receiving = conn.execute("SELECT COUNT(DISTINCT to_agent) FROM messages").fetchone()[0]
    today = _today_utc()
    today_count = conn.execute(
        "SELECT COUNT(*) FROM messages WHERE day=?", (today,)
    ).fetchone()[0]
    return {
        "total_messages": total,
        "agents_sending": agents_sending,
        "agents_receiving": agents_receiving,
        "messages_today": today_count,
    }
