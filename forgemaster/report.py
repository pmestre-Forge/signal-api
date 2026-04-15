"""
FORGEMASTER — Daily Email Report

Sends Pedro one email per day with everything he needs to know.
Uses Gmail MCP or falls back to file-based report.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

REPORT_DIR = Path(__file__).parent
API_URL = "https://signal-api-lively-sky-8407.fly.dev"
GITHUB_URL = "https://github.com/pmestre-Forge/signal-api"


def build_report(ops_report: dict, intel_entry: str) -> dict:
    """Build the daily report content."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    services = ops_report.get("services", {})
    bot = ops_report.get("bot", {})
    posts = ops_report.get("posts", {})
    pat = ops_report.get("github_pat", {})
    actions = ops_report.get("actions_taken", [])

    # Services status line
    svc_lines = []
    for name, status in services.items():
        s = status.get("status", "unknown")
        ms = status.get("ms", "?")
        icon = "OK" if s == "up" else "PROBLEM"
        svc_lines.append(f"  {name}: {icon} ({ms}ms)")

    # Build email body
    subject = f"Forgemaster Daily Report - {datetime.now(timezone.utc).strftime('%Y-%m-%d')}"

    body_lines = [
        f"FORGEMASTER DAILY REPORT",
        f"{today}",
        f"",
        f"--- SERVICES ---",
        *svc_lines,
        f"",
        f"--- BOT ---",
        f"  Status: {'RUNNING' if bot.get('alive') else 'DOWN'}",
        f"  Posts today: {posts.get('posts_today', 0)}",
        f"  Platforms: {', '.join(posts.get('platforms', []))}",
        f"  Total posts all time: {posts.get('total_posts', 0)}",
        f"",
        f"--- GITHUB PAT ---",
        f"  Expires: {pat.get('expires', 'unknown')}",
        f"  Days left: {pat.get('days_left', '?')}",
    ]

    if pat.get("urgent"):
        body_lines.append(f"  *** URGENT: PAT expires in {pat['days_left']} days. Renew at github.com ***")

    body_lines.extend([
        f"",
        f"--- ACTIONS TAKEN ---",
    ])
    if actions:
        for a in actions:
            body_lines.append(f"  - {a}")
    else:
        body_lines.append(f"  None needed. Everything running clean.")

    body_lines.extend([
        f"",
        f"--- INTELLIGENCE ---",
        intel_entry.strip() if intel_entry else "  No new data.",
        f"",
        f"--- LINKS ---",
        f"  API: {API_URL}",
        f"  GitHub: {GITHUB_URL}",
        f"  Docs: {API_URL}/docs",
        f"  Landing: {API_URL}/",
        f"",
        f"--- NEEDS YOUR HANDS ---",
    ])

    # Things that need Pedro
    needs_pedro = []
    if pat.get("urgent"):
        needs_pedro.append("Renew GitHub PAT (expires in {pat['days_left']} days)")
    if not bot.get("alive") and not any("restart" in a.lower() for a in actions):
        needs_pedro.append("Bot is down and couldn't auto-restart")

    if needs_pedro:
        for n in needs_pedro:
            body_lines.append(f"  - {n}")
    else:
        body_lines.append(f"  Nothing. All autonomous.")

    body = "\n".join(body_lines)

    return {
        "subject": subject,
        "body": body,
        "to": "pmestre@cloudbees.com",
    }


def save_report(report: dict) -> str:
    """Save report to file as backup."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    report_file = REPORT_DIR / f"report_{today}.txt"
    report_file.write_text(report["body"])
    return str(report_file)


if __name__ == "__main__":
    # Test with dummy data
    dummy_ops = {
        "services": {"api": {"status": "up", "ms": 120}, "memory": {"status": "up", "ms": 95}, "identity": {"status": "up", "ms": 88}},
        "bot": {"alive": True},
        "posts": {"posts_today": 4, "platforms": ["devto", "discord", "reddit"], "total_posts": 15},
        "github_pat": {"expires": "2026-04-23", "days_left": 8, "urgent": False},
        "actions_taken": [],
    }
    report = build_report(dummy_ops, "Test intelligence entry")
    print(report["subject"])
    print(report["body"])
