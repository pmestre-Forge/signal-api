"""
FORGEMASTER — Intelligence Module

Reads stats, tracks performance, searches for opportunities.
Writes evolving learnings to intelligence.md.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import httpx

INTEL_FILE = Path(__file__).parent / "intelligence.md"
API_URL = "https://signal-api-lively-sky-8407.fly.dev"
FORGE_ROOT = Path.home() / "OneDrive" / "Ambiente de Trabalho" / "Forge" / "forge-distro"


def get_devto_stats() -> list[dict]:
    """Get Dev.to article performance stats."""
    creds_path = FORGE_ROOT / "credentials" / "devto.json"
    if not creds_path.exists():
        return []

    try:
        creds = json.loads(creds_path.read_text())
        api_key = creds.get("api_key", "")
        if not api_key:
            return []

        r = httpx.get(
            "https://dev.to/api/articles/me",
            headers={"api-key": api_key},
            timeout=15,
        )
        if r.status_code != 200:
            return []

        articles = r.json()
        return [
            {
                "title": a.get("title", "")[:60],
                "url": a.get("url", ""),
                "views": a.get("page_views_count", 0),
                "reactions": a.get("positive_reactions_count", 0),
                "comments": a.get("comments_count", 0),
                "published": a.get("published_at", "")[:10],
            }
            for a in articles[:10]
        ]
    except Exception:
        return []


def get_api_stats() -> dict:
    """Get current API stats."""
    stats = {}
    try:
        r = httpx.get(f"{API_URL}/stats/memory", timeout=10)
        if r.status_code == 200:
            stats["memory"] = r.json()
    except Exception:
        pass

    try:
        r = httpx.get(f"{API_URL}/stats/identity", timeout=10)
        if r.status_code == 200:
            stats["identity"] = r.json()
    except Exception:
        pass

    return stats


def get_bot_performance() -> dict:
    """Analyze bot posting performance."""
    state_file = Path(__file__).parent.parent / "bot" / "state.json"
    if not state_file.exists():
        return {"total_posts": 0}

    try:
        state = json.loads(state_file.read_text())
        logs = state.get("log", [])

        platforms = {}
        for p in logs:
            plat = p.get("platform", "unknown")
            platforms[plat] = platforms.get(plat, 0) + 1

        return {
            "total_posts": len(logs),
            "by_platform": platforms,
            "latest": logs[-1] if logs else None,
        }
    except Exception:
        return {"total_posts": 0}


def update_intelligence(ops_report: dict) -> str:
    """Update intelligence.md with today's findings. Returns the new entry."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Gather data
    devto = get_devto_stats()
    api_stats = get_api_stats()
    bot_perf = get_bot_performance()

    # Build today's entry
    entry_lines = [f"\n## {today}\n"]

    # Services
    services = ops_report.get("services", {})
    svc_summary = ", ".join(f"{k}:{v.get('status','?')}" for k, v in services.items())
    entry_lines.append(f"**Services:** {svc_summary}")

    # Bot performance
    entry_lines.append(f"**Bot:** {bot_perf.get('total_posts', 0)} total posts, platforms: {bot_perf.get('by_platform', {})}")

    # Dev.to stats
    if devto:
        total_views = sum(a.get("views", 0) for a in devto)
        total_reactions = sum(a.get("reactions", 0) for a in devto)
        entry_lines.append(f"**Dev.to:** {len(devto)} articles, {total_views} total views, {total_reactions} reactions")
        # Best performer
        if devto:
            best = max(devto, key=lambda a: a.get("views", 0))
            entry_lines.append(f"**Top article:** {best['title']} ({best.get('views', 0)} views)")

    # API usage
    if api_stats:
        mem = api_stats.get("memory", {})
        ident = api_stats.get("identity", {})
        entry_lines.append(f"**Memory:** {mem.get('total_entries', 0)} entries, {mem.get('total_namespaces', 0)} namespaces")
        entry_lines.append(f"**Identity:** {ident.get('total_agents', 0)} agents, {ident.get('total_reviews', 0)} reviews")

    # Actions taken
    actions = ops_report.get("actions_taken", [])
    if actions:
        entry_lines.append(f"**Actions taken:** {'; '.join(actions)}")

    entry = "\n".join(entry_lines) + "\n"

    # Append to intelligence.md
    existing = ""
    if INTEL_FILE.exists():
        existing = INTEL_FILE.read_text()

    if not existing:
        existing = "# FORGEMASTER Intelligence Log\n\nEvolving record of operations, performance, and opportunities.\n"

    # Don't duplicate today's entry
    if f"## {today}" not in existing:
        INTEL_FILE.write_text(existing + entry)

    return entry


if __name__ == "__main__":
    print(update_intelligence({"services": {}, "actions_taken": []}))
