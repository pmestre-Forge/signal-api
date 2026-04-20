"""
Agent Config Store — persistent, structured operational config for AI agents.

Distinct from Memory (free-form KV): Config is typed, categorized, and exportable.
Use this to store schedules, rules, preferences, flags, and operational state.

Free tier: 50 entries per registered agent.
All operations free — adoption first.
"""

import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).parent / "data" / "config_store.db"
DB_PATH.parent.mkdir(exist_ok=True)

VALID_TYPES = {"schedule", "rule", "preference", "flag", "state"}
FREE_TIER_LIMIT = 50

_local = threading.local()


def _get_conn() -> sqlite3.Connection:
    if not hasattr(_local, "conn"):
        _local.conn = sqlite3.connect(str(DB_PATH), timeout=10)
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _local.conn.execute("""
            CREATE TABLE IF NOT EXISTS configs (
                agent_id TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                config_type TEXT NOT NULL DEFAULT 'preference',
                description TEXT DEFAULT '',
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                PRIMARY KEY (agent_id, key)
            )
        """)
        _local.conn.execute("CREATE INDEX IF NOT EXISTS idx_agent ON configs(agent_id)")
        _local.conn.execute("CREATE INDEX IF NOT EXISTS idx_type ON configs(agent_id, config_type)")
        _local.conn.commit()
    return _local.conn


def _count_entries(agent_id: str) -> int:
    conn = _get_conn()
    row = conn.execute("SELECT COUNT(*) FROM configs WHERE agent_id=?", (agent_id,)).fetchone()
    return row[0] if row else 0


def config_set(agent_id: str, key: str, value: str, config_type: str = "preference", description: str = "") -> dict:
    if config_type not in VALID_TYPES:
        return {"error": f"Invalid type. Must be one of: {', '.join(sorted(VALID_TYPES))}"}
    conn = _get_conn()
    now = time.time()
    # Check if key already exists (update is always allowed)
    existing = conn.execute(
        "SELECT key FROM configs WHERE agent_id=? AND key=?", (agent_id, key)
    ).fetchone()
    if not existing:
        count = _count_entries(agent_id)
        if count >= FREE_TIER_LIMIT:
            return {"error": f"Free tier limit of {FREE_TIER_LIMIT} entries reached. Delete unused entries first."}
    conn.execute(
        """INSERT INTO configs (agent_id, key, value, config_type, description, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(agent_id, key) DO UPDATE SET value=?, config_type=?, description=?, updated_at=?""",
        (agent_id, key, value, config_type, description, now, now, value, config_type, description, now),
    )
    conn.commit()
    return {
        "agent_id": agent_id,
        "key": key,
        "config_type": config_type,
        "stored": True,
        "updated_at": now,
    }


def config_get(agent_id: str, key: str) -> Optional[dict]:
    conn = _get_conn()
    row = conn.execute(
        "SELECT value, config_type, description, created_at, updated_at FROM configs WHERE agent_id=? AND key=?",
        (agent_id, key),
    ).fetchone()
    if not row:
        return None
    return {
        "agent_id": agent_id,
        "key": key,
        "value": row[0],
        "config_type": row[1],
        "description": row[2],
        "created_at": row[3],
        "updated_at": row[4],
    }


def config_delete(agent_id: str, key: str) -> bool:
    conn = _get_conn()
    cursor = conn.execute("DELETE FROM configs WHERE agent_id=? AND key=?", (agent_id, key))
    conn.commit()
    return cursor.rowcount > 0


def config_list(agent_id: str, config_type: Optional[str] = None) -> dict:
    conn = _get_conn()
    if config_type:
        rows = conn.execute(
            "SELECT key, value, config_type, description, updated_at FROM configs WHERE agent_id=? AND config_type=? ORDER BY updated_at DESC",
            (agent_id, config_type),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT key, value, config_type, description, updated_at FROM configs WHERE agent_id=? ORDER BY config_type, key",
            (agent_id,),
        ).fetchall()
    entries = [
        {"key": r[0], "value": r[1], "config_type": r[2], "description": r[3], "updated_at": r[4]}
        for r in rows
    ]
    return {
        "agent_id": agent_id,
        "count": len(entries),
        "limit": FREE_TIER_LIMIT,
        "entries": entries,
    }


def config_export(agent_id: str) -> dict:
    result = config_list(agent_id)
    return {
        "agent_id": agent_id,
        "exported_at": time.time(),
        "count": result["count"],
        "config": {e["key"]: {"value": e["value"], "config_type": e["config_type"], "description": e["description"]} for e in result["entries"]},
    }


def config_import(agent_id: str, bundle: dict, overwrite: bool = False) -> dict:
    """Import a config bundle. Keys that already exist are skipped unless overwrite=True."""
    imported = 0
    skipped = 0
    errors = []
    for key, entry in bundle.items():
        if not isinstance(entry, dict):
            errors.append(f"{key}: entry must be an object with 'value' field")
            continue
        value = entry.get("value", "")
        config_type = entry.get("config_type", "preference")
        description = entry.get("description", "")
        if not overwrite:
            existing = config_get(agent_id, key)
            if existing:
                skipped += 1
                continue
        result = config_set(agent_id, key, str(value), config_type, description)
        if "error" in result:
            errors.append(f"{key}: {result['error']}")
        else:
            imported += 1
    return {"agent_id": agent_id, "imported": imported, "skipped": skipped, "errors": errors}


def config_stats() -> dict:
    conn = _get_conn()
    total = conn.execute("SELECT COUNT(*), COUNT(DISTINCT agent_id) FROM configs").fetchone()
    by_type = conn.execute(
        "SELECT config_type, COUNT(*) FROM configs GROUP BY config_type ORDER BY COUNT(*) DESC"
    ).fetchall()
    return {
        "total_entries": total[0] or 0,
        "total_agents": total[1] or 0,
        "by_type": {r[0]: r[1] for r in by_type},
    }
