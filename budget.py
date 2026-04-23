"""
Agent Budget Tracker — per-agent LLM cost tracking with spend limits.

Agents record every model call. Limits auto-alert at 80% and block at 100%.
Free forever. Stickiness: your budget history and limits live here.

Endpoints (all free):
  POST /budget/{agent_id}/record   — log a model call
  PUT  /budget/{agent_id}/limits   — set daily/monthly caps
  GET  /budget/{agent_id}/usage    — spending summary (?period=day|month|all)
  GET  /budget/{agent_id}/check    — fast budget gate (call before each LLM call)
  GET  /stats/budget               — platform-wide stats
"""

import sqlite3
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).parent / "data" / "budget.db"
DB_PATH.parent.mkdir(exist_ok=True)

_local = threading.local()

FREE_RECORDS_PER_DAY = 1000


def _conn() -> sqlite3.Connection:
    if not hasattr(_local, "conn"):
        _local.conn = sqlite3.connect(str(DB_PATH), timeout=10)
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _local.conn.row_factory = sqlite3.Row
        _local.conn.executescript("""
            CREATE TABLE IF NOT EXISTS usage (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id      TEXT NOT NULL,
                model         TEXT NOT NULL DEFAULT '',
                input_tokens  INTEGER NOT NULL DEFAULT 0,
                output_tokens INTEGER NOT NULL DEFAULT 0,
                cost_usd      REAL NOT NULL DEFAULT 0.0,
                note          TEXT DEFAULT '',
                ts            REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_usage_agent ON usage(agent_id, ts);

            CREATE TABLE IF NOT EXISTS limits (
                agent_id    TEXT PRIMARY KEY,
                daily_usd   REAL,
                monthly_usd REAL,
                updated_at  REAL NOT NULL
            );
        """)
        _local.conn.commit()
    return _local.conn


def _now_utc() -> float:
    return datetime.now(timezone.utc).timestamp()


def _day_start() -> float:
    now = datetime.now(timezone.utc)
    return datetime(now.year, now.month, now.day, tzinfo=timezone.utc).timestamp()


def _month_start() -> float:
    now = datetime.now(timezone.utc)
    return datetime(now.year, now.month, 1, tzinfo=timezone.utc).timestamp()


def record_usage(
    agent_id: str,
    model: str = "",
    input_tokens: int = 0,
    output_tokens: int = 0,
    cost_usd: float = 0.0,
    note: str = "",
) -> dict:
    db = _conn()
    ts = _now_utc()
    db.execute(
        "INSERT INTO usage (agent_id, model, input_tokens, output_tokens, cost_usd, note, ts) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (agent_id, model, input_tokens, output_tokens, cost_usd, note, ts),
    )
    db.commit()

    # Check if any budget threshold crossed — return alert info
    status = check_budget(agent_id)
    return {
        "recorded": True,
        "agent_id": agent_id,
        "cost_usd": cost_usd,
        "budget_status": status,
    }


def set_limits(agent_id: str, daily_usd: Optional[float], monthly_usd: Optional[float]) -> dict:
    db = _conn()
    db.execute(
        "INSERT INTO limits (agent_id, daily_usd, monthly_usd, updated_at) VALUES (?, ?, ?, ?) "
        "ON CONFLICT(agent_id) DO UPDATE SET daily_usd=excluded.daily_usd, "
        "monthly_usd=excluded.monthly_usd, updated_at=excluded.updated_at",
        (agent_id, daily_usd, monthly_usd, _now_utc()),
    )
    db.commit()
    return {"agent_id": agent_id, "daily_usd": daily_usd, "monthly_usd": monthly_usd}


def get_usage(agent_id: str, period: str = "month") -> dict:
    db = _conn()
    if period == "day":
        since = _day_start()
        label = "today"
    elif period == "month":
        since = _month_start()
        label = "this_month"
    else:
        since = 0.0
        label = "all_time"

    row = db.execute(
        "SELECT COUNT(*) as calls, COALESCE(SUM(cost_usd),0) as total_cost, "
        "COALESCE(SUM(input_tokens),0) as input_tokens, "
        "COALESCE(SUM(output_tokens),0) as output_tokens "
        "FROM usage WHERE agent_id=? AND ts>=?",
        (agent_id, since),
    ).fetchone()

    lim = db.execute(
        "SELECT daily_usd, monthly_usd FROM limits WHERE agent_id=?", (agent_id,)
    ).fetchone()

    return {
        "agent_id": agent_id,
        "period": label,
        "calls": row["calls"],
        "cost_usd": round(row["total_cost"], 6),
        "input_tokens": row["input_tokens"],
        "output_tokens": row["output_tokens"],
        "limits": {
            "daily_usd": lim["daily_usd"] if lim else None,
            "monthly_usd": lim["monthly_usd"] if lim else None,
        },
    }


def check_budget(agent_id: str) -> dict:
    """Fast gate — call before each LLM call to see if agent is within budget."""
    db = _conn()

    lim = db.execute(
        "SELECT daily_usd, monthly_usd FROM limits WHERE agent_id=?", (agent_id,)
    ).fetchone()

    # No limits set → always ok
    if not lim or (lim["daily_usd"] is None and lim["monthly_usd"] is None):
        return {"ok": True, "agent_id": agent_id, "limits_set": False}

    daily_used = db.execute(
        "SELECT COALESCE(SUM(cost_usd),0) FROM usage WHERE agent_id=? AND ts>=?",
        (agent_id, _day_start()),
    ).fetchone()[0]

    monthly_used = db.execute(
        "SELECT COALESCE(SUM(cost_usd),0) FROM usage WHERE agent_id=? AND ts>=?",
        (agent_id, _month_start()),
    ).fetchone()[0]

    daily_lim = lim["daily_usd"]
    monthly_lim = lim["monthly_usd"]

    daily_pct = (daily_used / daily_lim * 100) if daily_lim else None
    monthly_pct = (monthly_used / monthly_lim * 100) if monthly_lim else None

    ok = True
    alerts = []
    if daily_lim and daily_used >= daily_lim:
        ok = False
        alerts.append("daily_limit_exceeded")
    elif daily_pct and daily_pct >= 80:
        alerts.append("daily_80pct_warning")

    if monthly_lim and monthly_used >= monthly_lim:
        ok = False
        alerts.append("monthly_limit_exceeded")
    elif monthly_pct and monthly_pct >= 80:
        alerts.append("monthly_80pct_warning")

    return {
        "ok": ok,
        "agent_id": agent_id,
        "limits_set": True,
        "daily": {
            "used_usd": round(daily_used, 6),
            "limit_usd": daily_lim,
            "pct": round(daily_pct, 1) if daily_pct is not None else None,
        },
        "monthly": {
            "used_usd": round(monthly_used, 6),
            "limit_usd": monthly_lim,
            "pct": round(monthly_pct, 1) if monthly_pct is not None else None,
        },
        "alerts": alerts,
    }


def budget_stats() -> dict:
    db = _conn()
    total = db.execute(
        "SELECT COUNT(DISTINCT agent_id) as agents, COUNT(*) as calls, "
        "COALESCE(SUM(cost_usd),0) as total_cost "
        "FROM usage"
    ).fetchone()
    limits_set = db.execute("SELECT COUNT(*) FROM limits").fetchone()[0]
    return {
        "total_agents_tracked": total["agents"],
        "total_calls_recorded": total["calls"],
        "total_cost_usd": round(total["total_cost"], 4),
        "agents_with_limits": limits_set,
    }
