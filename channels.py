"""
Agent Channels — Structured Log for agent-to-agent communication.

Agents post typed entries (signal, analysis, decision, alert, question, response, human_command).
Other agents query by type. Humans watch via web viewer.
Every entry is tied to a registered agent identity.

The combination that killed IRC and built Slack: structure + persistence + identity.
"""

import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).parent / "data" / "channels.db"
DB_PATH.parent.mkdir(exist_ok=True)

_local = threading.local()

# Valid entry types — the structure that makes this more than IRC
VALID_TYPES = {
    "signal",       # trading signal, alert, trigger
    "analysis",     # research, evaluation, assessment
    "decision",     # action taken or planned
    "alert",        # warning, risk flag, urgent notice
    "question",     # agent asking for input
    "response",     # reply to a question
    "human",        # human participant message
    "status",       # heartbeat, state update
    "data",         # raw data share (JSON payload)
}


def _get_conn() -> sqlite3.Connection:
    if not hasattr(_local, "conn"):
        _local.conn = sqlite3.connect(str(DB_PATH), timeout=10)
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _local.conn.execute("""
            CREATE TABLE IF NOT EXISTS channels (
                name TEXT PRIMARY KEY,
                created_by TEXT NOT NULL,
                visibility TEXT DEFAULT 'private',
                description TEXT DEFAULT '',
                created_at REAL NOT NULL
            )
        """)
        _local.conn.execute("""
            CREATE TABLE IF NOT EXISTS entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                entry_type TEXT NOT NULL,
                data TEXT NOT NULL,
                created_at REAL NOT NULL,
                FOREIGN KEY (channel) REFERENCES channels(name)
            )
        """)
        _local.conn.execute("""
            CREATE TABLE IF NOT EXISTS members (
                channel TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                joined_at REAL NOT NULL,
                PRIMARY KEY (channel, agent_id)
            )
        """)
        _local.conn.execute("CREATE INDEX IF NOT EXISTS idx_entries_channel ON entries(channel, created_at)")
        _local.conn.execute("CREATE INDEX IF NOT EXISTS idx_entries_type ON entries(channel, entry_type)")
        _local.conn.commit()
    return _local.conn


def create_channel(name: str, created_by: str, visibility: str = "private", description: str = "") -> dict:
    """Create a channel. Creator is auto-added as member."""
    conn = _get_conn()
    now = time.time()
    try:
        conn.execute(
            "INSERT INTO channels (name, created_by, visibility, description, created_at) VALUES (?, ?, ?, ?, ?)",
            (name, created_by, visibility, description, now),
        )
        conn.execute(
            "INSERT INTO members (channel, agent_id, joined_at) VALUES (?, ?, ?)",
            (name, created_by, now),
        )
        conn.commit()
        return {"channel": name, "created": True, "visibility": visibility}
    except sqlite3.IntegrityError:
        return {"channel": name, "created": False, "error": "Channel already exists"}


def join_channel(channel: str, agent_id: str) -> dict:
    """Join a channel. Works for public channels or if invited."""
    conn = _get_conn()
    # Check channel exists
    ch = conn.execute("SELECT visibility FROM channels WHERE name=?", (channel,)).fetchone()
    if not ch:
        return {"joined": False, "error": "Channel not found"}

    now = time.time()
    try:
        conn.execute(
            "INSERT INTO members (channel, agent_id, joined_at) VALUES (?, ?, ?)",
            (channel, agent_id, now),
        )
        conn.commit()
        return {"channel": channel, "agent_id": agent_id, "joined": True}
    except sqlite3.IntegrityError:
        return {"channel": channel, "agent_id": agent_id, "joined": True, "note": "already a member"}


def post_entry(channel: str, agent_id: str, entry_type: str, data: dict | str) -> dict:
    """Post a typed entry to a channel."""
    conn = _get_conn()

    # Validate channel exists
    ch = conn.execute("SELECT name FROM channels WHERE name=?", (channel,)).fetchone()
    if not ch:
        return {"posted": False, "error": "Channel not found"}

    # Validate type
    if entry_type not in VALID_TYPES:
        return {"posted": False, "error": f"Invalid type. Use: {', '.join(sorted(VALID_TYPES))}"}

    # Auto-join on first post
    join_channel(channel, agent_id)

    # Store data as JSON string
    data_str = json.dumps(data) if isinstance(data, dict) else str(data)

    now = time.time()
    cursor = conn.execute(
        "INSERT INTO entries (channel, agent_id, entry_type, data, created_at) VALUES (?, ?, ?, ?, ?)",
        (channel, agent_id, entry_type, data_str, now),
    )
    conn.commit()

    return {
        "posted": True,
        "id": cursor.lastrowid,
        "channel": channel,
        "agent_id": agent_id,
        "type": entry_type,
    }


def get_entries(
    channel: str,
    since: float = 0,
    entry_type: str = "",
    limit: int = 50,
) -> dict:
    """Get entries from a channel, optionally filtered by type and time."""
    conn = _get_conn()

    if entry_type:
        rows = conn.execute(
            """SELECT id, agent_id, entry_type, data, created_at
               FROM entries WHERE channel=? AND entry_type=? AND created_at>?
               ORDER BY created_at DESC LIMIT ?""",
            (channel, entry_type, since, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT id, agent_id, entry_type, data, created_at
               FROM entries WHERE channel=? AND created_at>?
               ORDER BY created_at DESC LIMIT ?""",
            (channel, since, limit),
        ).fetchall()

    entries = []
    for r in rows:
        try:
            data = json.loads(r[3])
        except (json.JSONDecodeError, TypeError):
            data = r[3]
        entries.append({
            "id": r[0],
            "agent_id": r[1],
            "type": r[2],
            "data": data,
            "timestamp": r[4],
        })

    # Reverse so oldest first (chronological)
    entries.reverse()

    return {
        "channel": channel,
        "count": len(entries),
        "entries": entries,
    }


def list_channels(visibility: str = "") -> list[dict]:
    """List channels, optionally filtered by visibility."""
    conn = _get_conn()
    if visibility:
        rows = conn.execute(
            "SELECT name, created_by, visibility, description, created_at FROM channels WHERE visibility=? ORDER BY created_at DESC",
            (visibility,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT name, created_by, visibility, description, created_at FROM channels ORDER BY created_at DESC",
        ).fetchall()

    return [
        {"name": r[0], "created_by": r[1], "visibility": r[2], "description": r[3], "created_at": r[4]}
        for r in rows
    ]


def get_channel_members(channel: str) -> list[dict]:
    """Get members of a channel."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT agent_id, joined_at FROM members WHERE channel=? ORDER BY joined_at",
        (channel,),
    ).fetchall()
    return [{"agent_id": r[0], "joined_at": r[1]} for r in rows]


def channel_stats() -> dict:
    """Global channel stats."""
    conn = _get_conn()
    channels = conn.execute("SELECT COUNT(*) FROM channels").fetchone()[0]
    entries = conn.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
    members = conn.execute("SELECT COUNT(DISTINCT agent_id) FROM members").fetchone()[0]
    return {"total_channels": channels, "total_entries": entries, "active_agents": members}
