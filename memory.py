"""
Agent Memory API — persistent key-value storage for AI agents.

Agents are stateless by default. This gives them memory.
Pay per read/write via x402 micropayments.
"""

import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Optional

# SQLite DB — persists across Fly.io stop/start cycles
DB_PATH = Path(__file__).parent / "data" / "memory.db"
DB_PATH.parent.mkdir(exist_ok=True)

# Thread-local connections (SQLite isn't thread-safe across connections)
_local = threading.local()


def _get_conn() -> sqlite3.Connection:
    if not hasattr(_local, "conn"):
        _local.conn = sqlite3.connect(str(DB_PATH), timeout=10)
        _local.conn.execute("PRAGMA journal_mode=WAL")  # better concurrent reads
        _local.conn.execute("""
            CREATE TABLE IF NOT EXISTS kv (
                namespace TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                PRIMARY KEY (namespace, key)
            )
        """)
        _local.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_ns ON kv(namespace)
        """)
        _local.conn.commit()
    return _local.conn


def memory_set(namespace: str, key: str, value: str) -> dict:
    """Store a value. Returns metadata."""
    conn = _get_conn()
    now = time.time()
    conn.execute(
        """INSERT INTO kv (namespace, key, value, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(namespace, key) DO UPDATE SET value=?, updated_at=?""",
        (namespace, key, value, now, now, value, now),
    )
    conn.commit()
    return {"namespace": namespace, "key": key, "stored": True, "bytes": len(value)}


def memory_get(namespace: str, key: str) -> Optional[dict]:
    """Retrieve a value. Returns None if not found."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT value, created_at, updated_at FROM kv WHERE namespace=? AND key=?",
        (namespace, key),
    ).fetchone()
    if not row:
        return None
    return {
        "namespace": namespace,
        "key": key,
        "value": row[0],
        "created_at": row[1],
        "updated_at": row[2],
    }


def memory_delete(namespace: str, key: str) -> bool:
    """Delete a value. Returns True if existed."""
    conn = _get_conn()
    cursor = conn.execute(
        "DELETE FROM kv WHERE namespace=? AND key=?",
        (namespace, key),
    )
    conn.commit()
    return cursor.rowcount > 0


def memory_list(namespace: str, limit: int = 100) -> dict:
    """List keys in a namespace."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT key, length(value), updated_at FROM kv WHERE namespace=? ORDER BY updated_at DESC LIMIT ?",
        (namespace, limit),
    ).fetchall()
    return {
        "namespace": namespace,
        "count": len(rows),
        "keys": [{"key": r[0], "bytes": r[1], "updated_at": r[2]} for r in rows],
    }


def memory_stats() -> dict:
    """Global stats."""
    conn = _get_conn()
    row = conn.execute("SELECT COUNT(*), COUNT(DISTINCT namespace), SUM(length(value)) FROM kv").fetchone()
    return {
        "total_entries": row[0] or 0,
        "total_namespaces": row[1] or 0,
        "total_bytes": row[2] or 0,
    }
