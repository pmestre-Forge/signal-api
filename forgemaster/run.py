"""
FORGEMASTER — Main Runner

Daily autonomous agent. Operates, fixes, learns, reports.
Run via Claude Code scheduled task at 10:30am daily.
"""

import sys
from pathlib import Path

# Add parent to path so imports work
sys.path.insert(0, str(Path(__file__).parent.parent / "bot"))
sys.path.insert(0, str(Path(__file__).parent))

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

    # --- Job 2: Auto-propose, review, execute ---
    print("\n[2/4] GOVERNANCE — auto-propose + review + execute...", flush=True)
    ceo_results: list = []
    exec_results: list = []
    auto_ideas: list = []
    try:
        # Step A: auto-proposer generates fresh ideas
        from auto_proposer import propose_and_submit
        auto_ideas = propose_and_submit(n=2)
        if auto_ideas:
            print(f"  Auto-proposer submitted {len(auto_ideas)} idea(s)", flush=True)
        else:
            print("  Auto-proposer: no ideas today", flush=True)

        # Step B: CEO + Legion review pending
        from ceo_agent import process_pending
        ceo_results = process_pending()
        if ceo_results:
            for r in ceo_results:
                if "error" in r:
                    print(f"  REVIEW ERR {r['proposal_id']}: {r['error']}", flush=True)
                    continue
                d = r["decision"]
                print(f"  {r['proposal_id']}: {d['decision']} (conf {d['confidence']:.0%}) — {d['reasoning'][:80]}", flush=True)

        # Step C: Executor auto-ships approved + safe proposals
        from executor import execute_all_approved
        exec_results = execute_all_approved()
        for r in exec_results:
            if r.get("executed"):
                print(f"  SHIPPED {r['proposal_id']}: {r.get('action')}", flush=True)
            elif "error" in r:
                print(f"  EXEC ERR {r['proposal_id']}: {r['error']}", flush=True)
            else:
                print(f"  skipped {r['proposal_id']}: {r.get('skipped','?')}", flush=True)
    except Exception as e:
        import traceback
        print(f"  Governance error: {e}", flush=True)
        traceback.print_exc()

    # --- Job 3: Intelligence ---
    print("\n[3/4] INTELLIGENCE — gathering data...", flush=True)
    intel_entry = update_intelligence(ops)
    # Append governance results into the intel entry so the email covers them
    if auto_ideas or ceo_results or exec_results:
        lines = ["", "--- Governance today ---"]
        if auto_ideas:
            lines.append(f"  Auto-proposed: {len(auto_ideas)}")
            for a in auto_ideas:
                lines.append(f"    * {a['title']} [{a['type']}] — {a.get('why_now','')}")
        if ceo_results:
            lines.append(f"  CEO decisions: {len(ceo_results)}")
            for r in ceo_results:
                if "error" in r:
                    lines.append(f"    FAILED {r['proposal_id']}: {r['error']}")
                    continue
                d = r["decision"]
                lines.append(f"    [{d['decision']}] {r['proposal_id']} (conf {d['confidence']:.0%})")
                lines.append(f"      {d['reasoning'][:200]}")
        if exec_results:
            shipped = [r for r in exec_results if r.get("executed")]
            if shipped:
                lines.append(f"  Auto-shipped: {len(shipped)}")
                for r in shipped:
                    lines.append(f"    * {r['proposal_id']}: {r.get('action')} — {r.get('notes','')[:150]}")
        intel_entry = (intel_entry or "") + "\n".join(lines)
    print(f"  Intelligence updated", flush=True)

    # --- Job 4: Report ---
    print("\n[4/4] REPORT — building daily report...", flush=True)
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
