"""
Run the Audit Legion against a single proposal.

Each of the 104 personas reacts to the proposal in-character (short response).
Then a synthesizer produces one verdict: KILL / PIVOT / INVEST / HOLD.

Cost: ~$0.50/proposal (104 short haiku calls + 1 sonnet synthesis).
"""
from __future__ import annotations
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from dotenv import load_dotenv

HERE = Path(__file__).parent
PROJECT_ROOT = HERE.parent.parent
load_dotenv(PROJECT_ROOT / "bot" / ".env", override=True)

PERSONAS = json.loads((HERE / "personas.json").read_text())["roles"]

# LLM wrapper auto-routes to Claude Code CLI (Pedro's Max plan, free) by default
sys.path.insert(0, str(HERE.parent))
from llm import get_client
client = get_client()


def _run_one(persona: dict, proposal: dict, platform_context: str) -> dict:
    model_map = {
        "haiku": "claude-3-5-haiku-20241022",
        "sonnet": "claude-sonnet-4-20250514",
    }
    model = model_map[persona["model"]]

    prompt = f"""You are playing the role of: {persona['title']}.

Your lens: {persona['lens']}

COMPANY CONTEXT:
{platform_context}

PROPOSAL UNDER REVIEW:
Title: {proposal['title']}
Type: {proposal['type']}
Proposed by: {proposal['proposer']}
Description:
{proposal['description']}

Respond in character. 2-4 sentences max. Start with either SHIP / DON'T SHIP / SHIP WITH CHANGES as the first token, then your reason. Be specific, brutal, and useful.
"""
    try:
        msg = client.messages.create(
            model=model,
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        return {
            "persona_id": persona["id"],
            "persona_title": persona["title"],
            "tier": persona["tier"],
            "response": msg.content[0].text.strip(),
        }
    except Exception as e:
        return {"persona_id": persona["id"], "persona_title": persona["title"], "tier": persona["tier"], "response": f"[ERROR: {e}]"}


def _platform_context() -> str:
    return """BotWire is a memory-first infrastructure platform for AI agents.
- Headline: persistent memory (free forever, pip install botwire)
- Adapters: LangChain, CrewAI, AutoGen, Claude, MCP
- Also offered free: agent identity, audit logs, DMs, config store, notifications, channels
- Paid (x402): trading signals, world-context API
- Stack: FastAPI + SQLite on Fly.io, ~61 SEO pages, Pro tier on waitlist
- Usage: near-zero paying customers, solo founder (Pedro), in early adoption
- Recent pivot: killed 6 products after a 728-persona audit, went all-in on memory
"""


def audit(proposal: dict, max_workers: int = 10) -> dict:
    """Run the full legion against one proposal. Returns synthesis + raw audits."""
    ctx = _platform_context()
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = [ex.submit(_run_one, p, proposal, ctx) for p in PERSONAS]
        results = [f.result() for f in as_completed(futures)]

    # Tally first-word signals
    tally = {"SHIP": 0, "DON'T SHIP": 0, "SHIP WITH CHANGES": 0, "OTHER": 0}
    for r in results:
        first = r["response"].strip().upper()
        if first.startswith("SHIP WITH CHANGES"):
            tally["SHIP WITH CHANGES"] += 1
        elif first.startswith("DON'T SHIP"):
            tally["DON'T SHIP"] += 1
        elif first.startswith("SHIP"):
            tally["SHIP"] += 1
        else:
            tally["OTHER"] += 1

    synthesis = _synthesize(proposal, results, tally, ctx)
    return {
        "proposal_id": proposal.get("id"),
        "raw_audits": results,
        "tally": tally,
        "synthesis": synthesis,
    }


def _synthesize(proposal: dict, audits: list[dict], tally: dict, context: str) -> dict:
    lines = []
    for a in audits[:80]:  # cap to ~80 for token budget
        lines.append(f"[{a['tier']}] {a['persona_title']}: {a['response'][:200]}")

    prompt = f"""You are the Chief of Staff synthesizing {len(audits)} employee reactions to this proposal for the CEO.

PROPOSAL:
Title: {proposal['title']}
Description: {proposal['description']}
Type: {proposal['type']}

VOTE TALLY:
- SHIP: {tally['SHIP']}
- DON'T SHIP: {tally["DON'T SHIP"]}
- SHIP WITH CHANGES: {tally['SHIP WITH CHANGES']}
- OTHER/UNCLEAR: {tally['OTHER']}

RAW REACTIONS (first 80):
{chr(10).join(lines)}

Produce a tight CEO brief:

**Legion verdict:** [SHIP / DON'T SHIP / SHIP WITH CHANGES — dominant signal]

**Strongest reasons to ship (3 bullets):**
- (from role X): ...

**Strongest reasons against (3 bullets):**
- (from role Y): ...

**Best suggested modification (if any):**
...

**Single biggest risk:**
...

**Recommended CEO action:**
APPROVE | REJECT | MODIFY — with a one-sentence rationale.

Be sharp, no corporate hedge. Max 250 words.
"""
    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=900,
        messages=[{"role": "user", "content": prompt}],
    )
    text = msg.content[0].text.strip()

    # Parse the top-line verdict
    verdict = "UNCLEAR"
    lower = text.lower()
    if "don't ship" in lower or "dont ship" in lower:
        verdict = "DON'T SHIP"
    elif "ship with changes" in lower:
        verdict = "SHIP WITH CHANGES"
    elif "ship" in lower:
        verdict = "SHIP"

    return {
        "verdict": verdict,
        "brief": text,
        "tally": tally,
        "persona_count": len(audits),
    }
