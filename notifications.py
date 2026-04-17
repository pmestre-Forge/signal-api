"""
Agent Notifications — subscribe to platform events, poll for triggers.

Agents register subscriptions for events they care about.
Free tier: 10 active subscriptions per agent.
Poll /notify/check/{agent_id} to see what fired since your last check.

Alert types:
  market_open   — US market opens (9:30 ET weekdays)
  market_close  — US market closes (16:00 ET weekdays)
  peer_review   — a specific agent gets a new review
  new_agent     — any new agent registers on the platform
"""

import json
import sqlite3
import threading
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).parent / "data" / "notifications.db"
DB_PATH.parent.mkdir(exist_ok=True)

FREE_TIER_SUBS = 10

VALID_ALERT_TYPES = {"market_open", "market_close", "peer_review", "new_agent"}

_local = threading.local()


def _get_conn() -> sqlite3.Connection:
    if not hasattr(_local, "conn"):
        _local.conn = sqlite3.connect(str(DB_PATH), timeout=10)
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _local.conn.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                params TEXT DEFAULT '{}',
                last_checked REAL NOT NULL,
                created_at REAL NOT NULL
            )
        """)
        _local.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_agent ON subscriptions(agent_id)
        """)
        _local.conn.commit()
    return _local.conn


def _et_now() -> datetime:
    """Current time in US/Eastern (no pytz needed — manual offset)."""
    utc_now = datetime.now(timezone.utc)
    # ET = UTC-5 (EST) or UTC-4 (EDT); use simple heuristic: March-Nov = EDT
    month = utc_now.month
    offset_hours = -4 if 3 <= month <= 11 else -5
    return utc_now + timedelta(hours=offset_hours)


def _check_market_open(last_checked: float) -> Optional[dict]:
    """Fires if current time is 09:30-09:35 ET on a weekday."""
    et = _et_now()
    if et.weekday() >= 5:  # weekend
        return None
    h, m = et.hour, et.minute
    if h == 9 and 30 <= m <= 35:
        window_start = et.replace(hour=9, minute=30, second=0, microsecond=0)
        if last_checked < window_start.timestamp() + 3600 * (et.utcoffset().total_seconds() / -3600 + 5):
            # avoid re-triggering in same window
            pass
        return {
            "alert_type": "market_open",
            "message": "US market is now open (9:30 ET)",
            "timestamp": et.isoformat(),
        }
    return None


def _check_market_close(last_checked: float) -> Optional[dict]:
    """Fires if current time is 16:00-16:05 ET on a weekday."""
    et = _et_now()
    if et.weekday() >= 5:
        return None
    h, m = et.hour, et.minute
    if h == 16 and 0 <= m <= 5:
        return {
            "alert_type": "market_close",
            "message": "US market has closed (16:00 ET)",
            "timestamp": et.isoformat(),
        }
    return None


def _check_peer_review(params: dict, last_checked: float) -> Optional[dict]:
    """Fires if target_agent_id received a new review since last_checked."""
    target_id = params.get("target_agent_id", "")
    if not target_id:
        return None
    try:
        identity_db = Path(__file__).parent / "data" / "identity.db"
        if not identity_db.exists():
            return None
        conn = sqlite3.connect(str(identity_db), timeout=5)
        row = conn.execute(
            "SELECT COUNT(*) FROM reviews WHERE target_id=? AND created_at>?",
            (target_id, last_checked),
        ).fetchone()
        conn.close()
        if row and row[0] > 0:
            return {
                "alert_type": "peer_review",
                "message": f"Agent {target_id} received {row[0]} new review(s)",
                "target_agent_id": target_id,
                "new_reviews": row[0],
            }
    except Exception:
        pass
    return None


def _check_new_agent(last_checked: float) -> Optional[dict]:
    """Fires if any new agent registered since last_checked."""
    try:
        identity_db = Path(__file__).parent / "data" / "identity.db"
        if not identity_db.exists():
            return None
        conn = sqlite3.connect(str(identity_db), timeout=5)
        row = conn.execute(
            "SELECT COUNT(*) FROM agents WHERE registered_at>?",
            (last_checked,),
        ).fetchone()
        conn.close()
        if row and row[0] > 0:
            return {
                "alert_type": "new_agent",
                "message": f"{row[0]} new agent(s) registered on the platform",
                "new_agents": row[0],
            }
    except Exception:
        pass
    return None


def subscribe(agent_id: str, alert_type: str, params: dict = None) -> dict:
    """Create a subscription. Free up to FREE_TIER_SUBS per agent."""
    if alert_type not in VALID_ALERT_TYPES:
        return {"error": f"Unknown alert type. Valid: {sorted(VALID_ALERT_TYPES)}"}

    conn = _get_conn()
    count = conn.execute(
        "SELECT COUNT(*) FROM subscriptions WHERE agent_id=?", (agent_id,)
    ).fetchone()[0]

    if count >= FREE_TIER_SUBS:
        return {
            "error": f"Free tier limit: {FREE_TIER_SUBS} subscriptions per agent",
            "current": count,
        }

    now = time.time()
    cur = conn.execute(
        "INSERT INTO subscriptions (agent_id, alert_type, params, last_checked, created_at) VALUES (?,?,?,?,?)",
        (agent_id, alert_type, json.dumps(params or {}), now, now),
    )
    conn.commit()

    return {
        "subscribed": True,
        "subscription_id": cur.lastrowid,
        "agent_id": agent_id,
        "alert_type": alert_type,
        "params": params or {},
        "note": f"Poll GET /notify/check/{agent_id} to receive triggered alerts",
    }


def check_alerts(agent_id: str) -> dict:
    """Return all triggered alerts for agent since last check. Updates last_checked."""
    conn = _get_conn()
    subs = conn.execute(
        "SELECT id, alert_type, params, last_checked FROM subscriptions WHERE agent_id=?",
        (agent_id,),
    ).fetchall()

    triggered = []
    now = time.time()

    for sub_id, alert_type, params_json, last_checked in subs:
        params = json.loads(params_json or "{}")
        alert = None

        if alert_type == "market_open":
            alert = _check_market_open(last_checked)
        elif alert_type == "market_close":
            alert = _check_market_close(last_checked)
        elif alert_type == "peer_review":
            alert = _check_peer_review(params, last_checked)
        elif alert_type == "new_agent":
            alert = _check_new_agent(last_checked)

        if alert:
            alert["subscription_id"] = sub_id
            triggered.append(alert)

        # Always update last_checked
        conn.execute(
            "UPDATE subscriptions SET last_checked=? WHERE id=?", (now, sub_id)
        )

    conn.commit()

    return {
        "agent_id": agent_id,
        "triggered": triggered,
        "total_triggered": len(triggered),
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "active_subscriptions": len(subs),
    }


def list_subscriptions(agent_id: str) -> dict:
    """List all subscriptions for an agent."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT id, alert_type, params, last_checked, created_at FROM subscriptions WHERE agent_id=? ORDER BY created_at DESC",
        (agent_id,),
    ).fetchall()

    return {
        "agent_id": agent_id,
        "subscriptions": [
            {
                "id": r[0],
                "alert_type": r[1],
                "params": json.loads(r[2] or "{}"),
                "last_checked": datetime.fromtimestamp(r[3], tz=timezone.utc).isoformat(),
                "created_at": datetime.fromtimestamp(r[4], tz=timezone.utc).isoformat(),
            }
            for r in rows
        ],
        "count": len(rows),
        "free_tier_limit": FREE_TIER_SUBS,
    }


def cancel_subscription(agent_id: str, sub_id: int) -> dict:
    """Cancel a subscription."""
    conn = _get_conn()
    cur = conn.execute(
        "DELETE FROM subscriptions WHERE id=? AND agent_id=?", (sub_id, agent_id)
    )
    conn.commit()
    if cur.rowcount == 0:
        return {"error": "Subscription not found or does not belong to this agent"}
    return {"cancelled": True, "subscription_id": sub_id}


def notification_stats() -> dict:
    """Global notification platform statistics."""
    conn = _get_conn()
    total_subs = conn.execute("SELECT COUNT(*) FROM subscriptions").fetchone()[0]
    unique_agents = conn.execute("SELECT COUNT(DISTINCT agent_id) FROM subscriptions").fetchone()[0]
    by_type = conn.execute(
        "SELECT alert_type, COUNT(*) FROM subscriptions GROUP BY alert_type"
    ).fetchall()

    return {
        "total_subscriptions": total_subs,
        "unique_agents": unique_agents,
        "subscriptions_by_type": {row[0]: row[1] for row in by_type},
        "alert_types": sorted(VALID_ALERT_TYPES),
        "free_tier": f"{FREE_TIER_SUBS} subscriptions per agent",
    }
