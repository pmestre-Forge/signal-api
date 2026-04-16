"""
Agent Identity & Reputation API — trust layer for AI agents.

Agents register, build reputation through transactions, and verify each other.
Pay per lookup via x402 micropayments. Registration is free.
"""

import hashlib
import sqlite3
import threading
import time
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).parent / "data" / "identity.db"
DB_PATH.parent.mkdir(exist_ok=True)

_local = threading.local()


def _get_conn() -> sqlite3.Connection:
    if not hasattr(_local, "conn"):
        _local.conn = sqlite3.connect(str(DB_PATH), timeout=10)
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _local.conn.execute("""
            CREATE TABLE IF NOT EXISTS agents (
                agent_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                wallet_address TEXT DEFAULT '',
                capabilities TEXT DEFAULT '[]',
                registered_at REAL NOT NULL,
                last_seen REAL NOT NULL,
                transactions_count INTEGER DEFAULT 0,
                reputation_score REAL DEFAULT 0.5
            )
        """)
        _local.conn.execute("""
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reviewer_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                score REAL NOT NULL,
                comment TEXT DEFAULT '',
                created_at REAL NOT NULL,
                FOREIGN KEY (target_id) REFERENCES agents(agent_id)
            )
        """)
        _local.conn.commit()
    return _local.conn


def _generate_id(name: str, wallet: str) -> str:
    """Generate deterministic agent ID from name + wallet."""
    raw = f"{name}:{wallet}:{time.time()}".encode()
    return f"agent_{hashlib.sha256(raw).hexdigest()[:16]}"


def register_agent(name: str, description: str = "", wallet_address: str = "", capabilities: list = None) -> dict:
    """Register a new agent identity. Free."""
    conn = _get_conn()
    import json
    agent_id = _generate_id(name, wallet_address)
    now = time.time()
    caps = json.dumps(capabilities or [])

    try:
        conn.execute(
            """INSERT INTO agents (agent_id, name, description, wallet_address, capabilities, registered_at, last_seen)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (agent_id, name, description, wallet_address, caps, now, now),
        )
        conn.commit()
        return {
            "agent_id": agent_id,
            "name": name,
            "registered": True,
            "reputation_score": 0.5,
        }
    except sqlite3.IntegrityError:
        return {"error": "Registration failed", "registered": False}


def lookup_agent(agent_id: str) -> Optional[dict]:
    """Look up an agent's identity and reputation."""
    conn = _get_conn()
    row = conn.execute(
        """SELECT agent_id, name, description, wallet_address, capabilities,
                  registered_at, last_seen, transactions_count, reputation_score
           FROM agents WHERE agent_id=?""",
        (agent_id,),
    ).fetchone()
    if not row:
        return None

    # Update last_seen
    conn.execute("UPDATE agents SET last_seen=? WHERE agent_id=?", (time.time(), agent_id))
    conn.commit()

    return {
        "agent_id": row[0],
        "name": row[1],
        "description": row[2],
        "wallet_address": row[3],
        "capabilities": row[4],
        "registered_at": row[5],
        "last_seen": row[6],
        "transactions_count": row[7],
        "reputation_score": round(row[8], 3),
    }


def search_agents(capability: str = "", limit: int = 20) -> list[dict]:
    """Search agents by capability."""
    limit = max(1, min(limit, 100))  # Cap at 100 to prevent DB dump
    conn = _get_conn()
    if capability:
        rows = conn.execute(
            """SELECT agent_id, name, description, capabilities, reputation_score, transactions_count
               FROM agents WHERE capabilities LIKE ? ORDER BY reputation_score DESC LIMIT ?""",
            (f"%{capability}%", limit),
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT agent_id, name, description, capabilities, reputation_score, transactions_count
               FROM agents ORDER BY reputation_score DESC LIMIT ?""",
            (limit,),
        ).fetchall()

    return [
        {
            "agent_id": r[0], "name": r[1], "description": r[2],
            "capabilities": r[3], "reputation_score": round(r[4], 3),
            "transactions_count": r[5],
        }
        for r in rows
    ]


def review_agent(reviewer_id: str, target_id: str, score: float, comment: str = "") -> dict:
    """Leave a review for an agent. Score 0.0-1.0."""
    conn = _get_conn()
    score = max(0.0, min(1.0, score))
    now = time.time()

    # Verify reviewer exists (prevent spoofing)
    reviewer = conn.execute("SELECT agent_id FROM agents WHERE agent_id=? OR name=?", (reviewer_id, reviewer_id)).fetchone()
    if not reviewer:
        return {"error": "Reviewer agent not found — must be registered", "reviewed": False}

    # Check target exists
    target = conn.execute("SELECT agent_id FROM agents WHERE agent_id=?", (target_id,)).fetchone()
    if not target:
        return {"error": "Target agent not found", "reviewed": False}

    # One review per reviewer-target pair (prevent spam)
    existing = conn.execute(
        "SELECT id FROM reviews WHERE reviewer_id=? AND target_id=?", (reviewer_id, target_id)
    ).fetchone()
    if existing:
        # Update existing review instead of adding duplicate
        conn.execute(
            "UPDATE reviews SET score=?, comment=?, created_at=? WHERE reviewer_id=? AND target_id=?",
            (score, comment, now, reviewer_id, target_id),
        )
    else:
        conn.execute(
            "INSERT INTO reviews (reviewer_id, target_id, score, comment, created_at) VALUES (?, ?, ?, ?, ?)",
            (reviewer_id, target_id, score, comment, now),
        )

    # Recalculate reputation as average of all reviews
    avg = conn.execute("SELECT AVG(score) FROM reviews WHERE target_id=?", (target_id,)).fetchone()[0]
    count = conn.execute("SELECT COUNT(*) FROM reviews WHERE target_id=?", (target_id,)).fetchone()[0]
    conn.execute(
        "UPDATE agents SET reputation_score=?, transactions_count=? WHERE agent_id=?",
        (avg or 0.5, count, target_id),
    )
    conn.commit()

    return {"reviewed": True, "target_id": target_id, "new_reputation": round(avg or 0.5, 3)}


def identity_stats() -> dict:
    """Global stats."""
    conn = _get_conn()
    agents = conn.execute("SELECT COUNT(*) FROM agents").fetchone()[0]
    reviews = conn.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
    return {"total_agents": agents, "total_reviews": reviews}
