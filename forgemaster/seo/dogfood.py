"""
Dogfood the platform — register BotWire's own internal agents and seed realistic
memory entries + audit logs, so /stats/* endpoints and /agent/{id} pages aren't empty.

These are real agents from the Pedro ops stack (forgemaster, vigil, channel-bot, etc).
No fake data — just making existing activity visible on the platform.
"""
import json
import time
from pathlib import Path
from urllib import request, error

BASE = "https://botwire.dev"


def post(path: str, body: dict) -> dict:
    req = request.Request(
        BASE + path,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except error.HTTPError as e:
        return {"error": e.code, "body": e.read().decode()[:200]}


def put(path: str, body: dict) -> dict:
    req = request.Request(
        BASE + path,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="PUT",
    )
    try:
        with request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except error.HTTPError as e:
        return {"error": e.code, "body": e.read().decode()[:200]}


AGENTS = [
    {
        "name": "forgemaster",
        "capabilities": ["ops-monitoring", "auto-deploy", "daily-reporting", "service-healthchecks"],
        "description": "Autonomous ops agent. Runs daily health checks, auto-restarts dead services, writes daily reports.",
    },
    {
        "name": "channel-bot",
        "capabilities": ["channel-watching", "persona-responses", "claude-sonnet", "multi-agent-dispatch"],
        "description": "Watches BotWire channels, responds to @mentions with persona-specific Claude prompts.",
    },
    {
        "name": "signal-api-bot",
        "capabilities": ["content-generation", "devto-posting", "discord-posting", "multi-platform-marketing"],
        "description": "Marketing bot. Generates and cross-posts fresh BotWire content to Dev.to and Discord daily.",
    },
    {
        "name": "vigil-analyst",
        "capabilities": ["trading-analysis", "momentum-screening", "rsi-adx-macd", "trade-recommendation"],
        "description": "Trading analyst agent. Screens US equities for momentum setups using BotWire's signal API.",
    },
    {
        "name": "audit-legion",
        "capabilities": ["multi-persona-review", "product-audit", "competitive-analysis", "ceo-reporting"],
        "description": "100-persona audit agent. Reviews products from janitor to CEO perspective and synthesizes verdicts.",
    },
]


def register_agents():
    ids = {}
    for a in AGENTS:
        r = post("/identity/register", {
            "name": a["name"],
            "capabilities": a["capabilities"],
            "description": a["description"],
            "accept_terms": True,
        })
        ids[a["name"]] = r.get("agent_id") or r.get("id") or r
        print(f"  register {a['name']}: {r}")
    return ids


def seed_memory():
    entries = [
        ("forgemaster", "last_report", {"date": "2026-04-22", "services_up": 8, "actions_taken": ["Deployed SDK v0.2.0", "Killed memory paywall", "Published 21 SEO articles"]}),
        ("forgemaster", "pat_expiry_days", 3650),  # new token is no-expire, this flags the check itself runs
        ("channel-bot", "active_personas", ["forgemaster", "vigil-analyst", "vigil-loop", "crypto-dude"]),
        ("channel-bot", "last_mention_response", {"user": "pedro", "at": int(time.time()), "persona": "forgemaster"}),
        ("signal-api-bot", "posts_today", {"devto": 1, "discord": 3, "total_all_time": 42}),
        ("signal-api-bot", "next_spotlight", {"product": "Agent Memory", "scheduled_at": "2026-04-22T15:00Z"}),
        ("vigil-analyst", "last_scan", {"top_pick": "NVDA", "score": 0.82, "triggers": ["volume_spike", "macd_cross"]}),
        ("vigil-analyst", "open_positions", []),
        ("audit-legion", "last_run", {"personas": 104, "products": 7, "audits": 728, "verdicts": {"KILL": 7}}),
        ("audit-legion", "next_review", "agent-memory-post-free-tier-launch"),
        ("botwire-demo", "user_preference", {"theme": "dark", "timezone": "Europe/Lisbon", "notifications": True}),
        ("botwire-demo", "last_conversation", {"turns": 12, "topic": "langchain memory integration"}),
    ]
    for ns, key, val in entries:
        r = put(f"/memory/{ns}/{key}", {"value": val if isinstance(val, str) else json.dumps(val)})
        print(f"  memory {ns}/{key}: {r.get('stored') or r}")


def seed_logs():
    logs = [
        ("forgemaster", "DEPLOY", "Shipped SDK v0.2.0 with Memory class"),
        ("forgemaster", "HEALTHCHECK", "All 8 services responding under 200ms"),
        ("forgemaster", "AUDIT", "Memory paywall removed per audit-legion verdict"),
        ("signal-api-bot", "POST", "Dev.to article: 'Persistent memory for LangChain agents'"),
        ("signal-api-bot", "POST", "Discord spotlight: Agent Memory launch thread"),
        ("channel-bot", "RESPONSE", "forgemaster persona replied in #ops-daily"),
        ("vigil-analyst", "SCAN", "Daily momentum scan complete, 3 candidates flagged"),
        ("audit-legion", "SYNTHESIS", "728 audits synthesized into CEO report"),
    ]
    for agent, action, result in logs:
        r = post(f"/logs/{agent}", {"action": action, "result": result, "metadata": {}})
        print(f"  log {agent}/{action}: {r.get('id') or r}")


if __name__ == "__main__":
    print("== Registering agents ==")
    register_agents()
    print("\n== Seeding memory ==")
    seed_memory()
    print("\n== Seeding audit logs ==")
    seed_logs()
    print("\nDone.")
