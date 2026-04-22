"""
CEO Agent — reviews legion synthesis and makes the final call.

The CEO doesn't just echo the legion. It weighs:
- Current platform priorities (memory-first, adoption over revenue right now)
- Cost of being wrong (irreversible > reversible)
- Strategic fit with the pivot
- Pedro's documented preferences (from MEMORY.md and PLAYBOOK.md)

Output: APPROVE / REJECT / MODIFY + reasoning + execution_hint.
"""
from __future__ import annotations
import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from anthropic import Anthropic

PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / "bot" / ".env", override=True)

sys.path.insert(0, str(Path(__file__).parent))
from audit_legion.audit_proposal import audit
import proposals as prop_store

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


CEO_SYSTEM = """You are the acting CEO of BotWire, a solo-founder AI agent infrastructure company.

Current priorities, in order:
1. Make persistent memory the best free/cheap option for AI agents.
2. Grow adoption (pip installs, GitHub stars, waitlist signups) over revenue — for now.
3. Keep the platform running with zero downtime on a single Fly.io machine.
4. Don't over-commit Pedro (solo founder). Any proposal that requires lots of ongoing human effort is suspect.
5. Preserve optionality — reversible actions get benefit of the doubt, irreversible actions need strong justification.

Anti-patterns to reject reflexively:
- Building new paid services that compete with free tiers of established players
- Anything that reintroduces the x402 paywall on Memory (that was the mistake)
- Features that require signups, OAuth, or "contact sales"
- Scope expansion beyond agent-memory while the core isn't winning yet
- Proposals that replicate an already-rejected past product

Style:
- Direct, builder-to-builder. No corporate hedging.
- If the legion is divided, lean toward REJECT or MODIFY (default to saying no).
- Mention specific roles from the legion when they made the key point.
"""


def decide(proposal: dict, legion_synthesis: dict) -> dict:
    """Given a proposal + legion synthesis, return a CEO decision."""
    prompt = f"""The Audit Legion ({legion_synthesis['persona_count']} personas) reviewed this proposal.

PROPOSAL:
Title: {proposal['title']}
Type: {proposal['type']}
Proposed by: {proposal['proposer']}
Description:
{proposal['description']}

LEGION VERDICT: {legion_synthesis['verdict']}
LEGION TALLY: {json.dumps(legion_synthesis['tally'])}

LEGION BRIEF:
{legion_synthesis['brief']}

Make the CEO decision. Output JSON ONLY:
{{
  "decision": "APPROVE" | "REJECT" | "MODIFY",
  "confidence": 0.0-1.0,
  "reasoning": "2-3 sentences. Cite specific legion roles where relevant.",
  "execution_hint": "If APPROVE, what's the first concrete step? If MODIFY, what's the specific change? If REJECT, what signal would flip it later?",
  "safe_to_auto_execute": true | false
}}

safe_to_auto_execute is TRUE only for small, reversible content additions (new article, bot copy tweak, new landing block). Pricing, deletions, infra changes, or anything irreversible must be FALSE.
"""
    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=800,
        system=CEO_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    text = msg.content[0].text.strip()
    # Extract JSON (Claude sometimes wraps in markdown)
    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        # Fallback: safe default
        return {
            "decision": "REJECT",
            "confidence": 0.3,
            "reasoning": f"CEO output was not valid JSON. Raw: {text[:200]}",
            "execution_hint": "Re-run with clearer instructions.",
            "safe_to_auto_execute": False,
        }


def review_proposal(pid: str) -> dict:
    """Full loop for one proposal: audit + synthesize + decide + save."""
    p = prop_store.load(pid)
    if not p:
        raise ValueError(f"Proposal not found: {pid}")

    prop_store.set_status(pid, "auditing")

    # Run the legion
    print(f"[ceo_agent] Running legion against {pid} — '{p.title}'...")
    legion = audit(p.to_dict())
    synthesis = legion["synthesis"]

    # CEO decision
    print(f"[ceo_agent] Legion verdict: {synthesis['verdict']}. Asking CEO...")
    decision = decide(p.to_dict(), synthesis)
    print(f"[ceo_agent] CEO decision: {decision['decision']} (confidence {decision['confidence']})")

    # Persist
    status = {"APPROVE": "approved", "REJECT": "rejected", "MODIFY": "modify"}.get(decision["decision"], "pending")
    prop_store.set_status(
        pid,
        status,
        legion_verdict=synthesis,
        ceo_decision=decision,
    )

    return {
        "proposal_id": pid,
        "legion": synthesis,
        "decision": decision,
        "status": status,
    }


def process_pending() -> list[dict]:
    """Process all pending proposals. Called by daily forgemaster."""
    pending = prop_store.list_pending()
    if not pending:
        return []
    print(f"[ceo_agent] {len(pending)} pending proposal(s). Reviewing...")
    results = []
    for p in pending:
        try:
            r = review_proposal(p.id)
            results.append(r)
        except Exception as e:
            print(f"[ceo_agent] Error reviewing {p.id}: {e}")
            prop_store.set_status(p.id, "failed", executor_notes=str(e))
            results.append({"proposal_id": p.id, "error": str(e)})
    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="CEO agent — review a proposal or all pending.")
    parser.add_argument("--id", help="Specific proposal ID to review")
    parser.add_argument("--all-pending", action="store_true", help="Review all pending proposals")
    args = parser.parse_args()

    if args.id:
        r = review_proposal(args.id)
        print(json.dumps(r, indent=2))
    elif args.all_pending:
        rs = process_pending()
        print(json.dumps(rs, indent=2))
    else:
        pending = prop_store.list_pending()
        print(f"Pending proposals: {len(pending)}")
        for p in pending:
            print(f"  {p.id} [{p.type}] {p.title}")
