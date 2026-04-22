"""
Audit Legion — 100 agents audit each BotWire product.

Each persona gets a sharp, role-specific lens.
Results aggregated into CEO report.
"""
import json
import os
import sys
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from anthropic import Anthropic
except ImportError:
    print("pip install anthropic")
    sys.exit(1)

# Load .env from bot/
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / "bot" / ".env", override=True)

HERE = Path(__file__).parent
PERSONAS = json.loads((HERE / "personas.json").read_text())["roles"]
REPORTS_DIR = HERE / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

PRODUCTS = [
    {
        "id": "signals",
        "name": "Trading Signals API",
        "pitch": "GET /signal/{ticker} returns BUY/SELL/HOLD for US equities with RSI/ADX/MACD/volume scoring. $0.005/call via x402. Also /scan/momentum ($0.01) and /risk ($0.01).",
        "stats": "Usage: zero paying customers. No reported revenue."
    },
    {
        "id": "memory",
        "name": "Agent Memory",
        "pitch": "Persistent key-value storage for AI agents. PUT/GET /memory/{namespace}/{key}. $0.002 write, $0.001 read. Solves statelessness between agent runs.",
        "stats": "Usage: 0 namespaces, 0 entries, 0 bytes stored."
    },
    {
        "id": "identity",
        "name": "Agent Identity & Reputation",
        "pitch": "Register agents (free), lookup ($0.001), search by capability ($0.002), review ($0.003). Agents can verify each other before transacting.",
        "stats": "Usage: 0 agents registered, 0 reviews."
    },
    {
        "id": "logs",
        "name": "Agent Audit Logs",
        "pitch": "Free tier (100/day). POST /logs/{agent_id} records actions. GET /logs reads history. For agent debugging and compliance trails.",
        "stats": "Usage: 0 entries, 0 active agents today."
    },
    {
        "id": "notifications",
        "name": "Agent Notifications",
        "pitch": "Free (10 subs/agent). Subscribe to market_open, market_close, peer_review, new_agent. Poll GET /notify/check/{agent_id}.",
        "stats": "Usage: 1 subscription (likely internal test)."
    },
    {
        "id": "config",
        "name": "Agent Config Store",
        "pitch": "Free (50 entries/agent). Typed config (schedule/rule/preference/flag/state) with export/import bundles. PUT/GET /config/{agent_id}/{key}.",
        "stats": "Usage: 0 entries, 0 agents."
    },
    {
        "id": "dm",
        "name": "Agent-to-Agent DMs",
        "pitch": "Free (50/day). POST /dm/send lets any agent message another. Inbox and thread views. Agent-to-agent coordination primitive.",
        "stats": "Usage: 0 messages, 0 senders, 0 receivers."
    },
]

PLATFORM_CONTEXT = """
BotWire is a FastAPI service at https://botwire.dev. All paid endpoints use x402 micropayments in USDC on Base L2. No signup, no API keys — agent wallet pays per call.

Stack: FastAPI, Python, SQLite, yfinance, deployed on Fly.io (single machine).
Source: https://github.com/pmestre-Forge/signal-api (MIT).
Landing page: https://botwire.dev
Docs: https://botwire.dev/docs, https://botwire.dev/llms.txt

Overall usage across all 7 products: essentially zero external paying users after ~1 week live.
Marketing: auto-bot posts to Dev.to and Discord. Twitter API credits exhausted. Reddit self-service killed.
"""


def run_audit(persona: dict, product: dict) -> dict:
    model = "claude-haiku-4-5" if persona["model"] == "haiku" else "claude-sonnet-4-20250514"
    # Fallback for name changes
    model_map = {
        "haiku": "claude-3-5-haiku-20241022",
        "sonnet": "claude-sonnet-4-20250514",
    }
    model = model_map[persona["model"]]

    prompt = f"""You are playing the role of: {persona['title']}.

Your lens: {persona['lens']}

PLATFORM CONTEXT:
{PLATFORM_CONTEXT}

PRODUCT YOU ARE AUDITING:
Name: {product['name']}
Pitch: {product['pitch']}
Current traction: {product['stats']}

Respond in character. Be brutally honest. 2-5 sentences max. No preamble, no disclaimers, no hedging. Start your response directly.
"""

    try:
        msg = client.messages.create(
            model=model,
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        return {
            "persona_id": persona["id"],
            "persona_title": persona["title"],
            "tier": persona["tier"],
            "product_id": product["id"],
            "product_name": product["name"],
            "response": msg.content[0].text.strip(),
            "model": persona["model"],
        }
    except Exception as e:
        return {
            "persona_id": persona["id"],
            "persona_title": persona["title"],
            "tier": persona["tier"],
            "product_id": product["id"],
            "product_name": product["name"],
            "response": f"[ERROR: {e}]",
            "model": persona["model"],
        }


def main():
    tasks = [(p, prod) for p in PERSONAS for prod in PRODUCTS]
    print(f"Running {len(tasks)} audits ({len(PERSONAS)} personas x {len(PRODUCTS)} products)...")

    results = []
    start = time.time()
    with ThreadPoolExecutor(max_workers=10) as ex:
        futures = {ex.submit(run_audit, p, prod): (p, prod) for p, prod in tasks}
        for i, fut in enumerate(as_completed(futures), 1):
            r = fut.result()
            results.append(r)
            if i % 25 == 0:
                elapsed = time.time() - start
                print(f"  {i}/{len(tasks)} done ({elapsed:.0f}s)")

    out = REPORTS_DIR / "raw_audits.json"
    out.write_text(json.dumps(results, indent=2))
    print(f"\nWrote {len(results)} audits to {out}")
    print(f"Total time: {time.time()-start:.0f}s")


if __name__ == "__main__":
    main()
