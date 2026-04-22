"""
Auto-proposer — Forgemaster writes its own proposals.

Every daily cycle, reads platform state (stats, recent logs, waitlist count,
sitemap) and asks Claude to generate 1-3 proposal ideas that would plausibly
move memory adoption forward. Each idea gets submitted as a proposal.

The Legion + CEO then decide what to actually do. Closes the autonomy loop.
"""
from __future__ import annotations
import json
import os
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any
from dotenv import load_dotenv
from anthropic import Anthropic

PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / "bot" / ".env", override=True)

sys.path.insert(0, str(Path(__file__).parent))
import proposals as prop_store

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

BASE = "https://botwire.dev"


def _j(path: str) -> Any:
    try:
        with urllib.request.urlopen(BASE + path, timeout=10) as r:
            return json.loads(r.read())
    except Exception:
        return None


def _platform_state() -> dict:
    """Snapshot everything useful for generating proposals."""
    return {
        "identity": _j("/stats/identity") or {},
        "memory": _j("/stats/memory") or {},
        "logs": _j("/stats/logs") or {},
        "notifications": _j("/stats/notifications") or {},
        "config": _j("/stats/config") or {},
        "dm": _j("/stats/dm") or {},
        "waitlist": _j("/waitlist/stats") or {},
        "existing_proposals": [
            {"title": p.title, "type": p.type, "status": p.status, "decision": (p.ceo_decision or {}).get("decision")}
            for p in prop_store.list_all()[:20]
        ],
    }


def _read_article_slugs() -> list[str]:
    """Existing article slugs, so auto-proposer doesn't duplicate."""
    articles_dir = PROJECT_ROOT / "static" / "articles"
    return sorted(f.stem for f in articles_dir.glob("*.html") if f.stem != "index")


def generate_proposals(n: int = 2) -> list[dict]:
    """Ask Claude to generate N plausible proposals given current state."""
    state = _platform_state()
    slugs = _read_article_slugs()

    prompt = f"""You are the acting VP of Product at BotWire. Your job: propose 1-3 small, cheap experiments that could plausibly move memory adoption forward.

CURRENT STATE:
- Waitlist signups: {state['waitlist'].get('waitlist_size', 0)}
- Registered agents: {state['identity'].get('total_agents', 0)}
- Memory entries stored: {state['memory'].get('total_entries', 0)}
- Memory namespaces: {state['memory'].get('total_namespaces', 0)}
- Total audit logs: {state['logs'].get('total_entries', 0)}
- Notifications subscribed: {state['notifications'].get('unique_agents', 0)}

RECENTLY REVIEWED PROPOSALS (avoid duplicating):
{json.dumps(state['existing_proposals'], indent=2)}

EXISTING SEO ARTICLES (do not propose duplicates):
{', '.join(slugs[:80])}
... (total: {len(slugs)})

PLATFORM CONSTRAINTS:
- Solo founder, so NO proposal that requires lots of ongoing human effort
- Memory-first strategy — reject anything that distracts from that
- Adoption > revenue right now; free/cheap beats paid
- x402 paywall on Memory is a NO-GO (that was the mistake we pivoted away from)
- Irreversible proposals need exceptional justification

Good shapes for proposals:
- A new SEO article targeting a specific long-tail query (type: "content")
- A small copy tweak to landing/pricing/bot rotation (type: "positioning")
- A tiny adapter for a hot framework (type: "feature")
- A partnership outreach (type: "partnership")
- A small bot/ops optimization (type: "infra")

BAD shapes:
- New paid tiers
- Products in adjacent categories (analytics, vector DB, training)
- Anything that requires pedro to do customer calls

Output ONLY a JSON array of 1-3 proposals:
[
  {{
    "title": "short, specific",
    "type": "content|feature|positioning|partnership|infra|product|pricing",
    "description": "3-6 sentences. If it's an ADD_ARTICLE, start description with 'ADD_ARTICLE slug=X title=Y query=Z keywords=a,b intent=who-it's-for', then a blank line, then narrative.",
    "why_now": "one sentence — the signal that triggered this",
    "expected_cost": "$ or hours"
  }},
  ...
]

IMPORTANT: if proposing ADD_ARTICLE, use the exact format above and ensure the slug is new (not in the existing slugs list).
"""
    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2500,
        messages=[{"role": "user", "content": prompt}],
    )
    text = msg.content[0].text.strip()
    # Strip markdown code fence if present
    if "```" in text:
        m = text.split("```")
        for chunk in m:
            if chunk.strip().startswith("json"):
                text = chunk[4:].strip()
                break
            if chunk.strip().startswith("["):
                text = chunk.strip()
                break

    try:
        ideas = json.loads(text)
    except json.JSONDecodeError:
        print(f"[auto_proposer] Failed to parse JSON: {text[:200]}")
        return []
    if not isinstance(ideas, list):
        return []
    return ideas[:n]


def propose_and_submit(n: int = 2) -> list[dict]:
    """Generate proposals and submit each to the proposal queue."""
    ideas = generate_proposals(n=n)
    submitted = []
    for idea in ideas:
        try:
            p = prop_store.create(
                title=idea["title"],
                description=idea["description"],
                ptype=idea.get("type", "content"),
                proposer="auto_proposer",
            )
            submitted.append({"id": p.id, "title": p.title, "type": p.type, "why_now": idea.get("why_now")})
            print(f"[auto_proposer] submitted {p.id}: {p.title}")
        except Exception as e:
            print(f"[auto_proposer] submit failed: {e}")
    return submitted


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", type=int, default=2, help="How many proposals to generate")
    parser.add_argument("--dry-run", action="store_true", help="Just print, don't submit")
    args = parser.parse_args()

    if args.dry_run:
        ideas = generate_proposals(n=args.n)
        print(json.dumps(ideas, indent=2))
    else:
        r = propose_and_submit(n=args.n)
        print(json.dumps(r, indent=2))
