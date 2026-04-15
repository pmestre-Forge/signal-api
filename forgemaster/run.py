"""
FORGEMASTER — Main Runner

Daily autonomous agent. Operates, fixes, learns, reports.
Run via Claude Code scheduled task at 10:30am daily.
"""

import sys
from pathlib import Path

# Add parent to path so imports work
sys.path.insert(0, str(Path(__file__).parent.parent / "bot"))

from operate import run_operations
from intelligence import update_intelligence
from report import build_report, save_report
from emailer import send_email


def run_forgemaster() -> dict:
    """Execute the full Forgemaster daily cycle."""

    print("=" * 60, flush=True)
    print("FORGEMASTER — Daily Cycle", flush=True)
    print("=" * 60, flush=True)

    # --- Job 1: Operate ---
    print("\n[1/3] OPERATE — checking everything...", flush=True)
    ops = run_operations()

    services = ops.get("services", {})
    for name, s in services.items():
        print(f"  {name}: {s.get('status', '?')} ({s.get('ms', '?')}ms)", flush=True)

    bot_alive = ops.get("bot", {}).get("alive", False)
    print(f"  bot: {'alive' if bot_alive else 'DEAD'}", flush=True)
    print(f"  posts today: {ops.get('posts', {}).get('posts_today', 0)}", flush=True)

    if ops.get("actions_taken"):
        for a in ops["actions_taken"]:
            print(f"  ACTION: {a}", flush=True)

    # --- Job 2: Intelligence ---
    print("\n[2/3] INTELLIGENCE — gathering data...", flush=True)
    intel_entry = update_intelligence(ops)
    print(f"  Intelligence updated", flush=True)

    # --- Job 3: Report ---
    print("\n[3/3] REPORT — building daily report...", flush=True)
    report = build_report(ops, intel_entry)

    # Save to file
    report_path = save_report(report)
    print(f"  Report saved: {report_path}", flush=True)

    # Send email
    email_sent = send_email(report["subject"], report["body"], report["to"])
    print(f"  Email: {'SENT' if email_sent else 'saved to file only (no app password)'}", flush=True)

    print("\n" + "=" * 60, flush=True)
    print("FORGEMASTER — Cycle complete", flush=True)
    print("=" * 60, flush=True)

    return {
        "ops": ops,
        "intel": intel_entry,
        "report": report,
        "report_path": report_path,
    }


if __name__ == "__main__":
    result = run_forgemaster()
    print("\n--- REPORT PREVIEW ---")
    print(result["report"]["body"])
