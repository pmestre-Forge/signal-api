"""
AI-powered content generator for Signal API marketing.

Uses Anthropic Claude to generate fresh posts every cycle.
Falls back to static content from content.py if API unavailable.
"""

import json
import logging
import os
from pathlib import Path

log = logging.getLogger("signal-bot")

PRODUCT_CONFIG = json.loads((Path(__file__).parent / "product_config.json").read_text())

# Product rotation — each day focuses on ONE product
PRODUCT_ROTATION = [
    {
        "name": "Trading Signals",
        "focus": "Momentum trading signals API (RSI, ADX, MACD, volume). BUY/SELL/HOLD for US stocks. $0.005/call.",
        "endpoint": "GET /signal/{ticker}",
    },
    {
        "name": "Agent Memory",
        "focus": "Persistent key-value storage for AI agents. Agents forget everything between runs. This fixes that. $0.001/read, $0.002/write.",
        "endpoint": "PUT /memory/{ns}/{key}",
    },
    {
        "name": "Agent Identity",
        "focus": "Trust layer for AI agents. Register (free), search by capability, leave reputation reviews. Agents can verify each other before transacting.",
        "endpoint": "POST /identity/register (free), GET /identity/lookup",
    },
    {
        "name": "World Context",
        "focus": "AI agents don't know what time it is, what timezone you're in, or if markets are open. One API call returns: local time, DST, market hours across 10 exchanges, holidays, business hours. $0.005/call.",
        "endpoint": "GET /context?tz=Europe/Lisbon&country=PT",
    },
    {
        "name": "Agent Heartbeat Monitor",
        "focus": "Is your AI agent alive? Track uptime with a one-liner: POST /heartbeat/{agent_id} every 60s. Get alive/degraded/dead status, uptime %, streak tracking. Free. Public profile page at /agent/{id}.",
        "endpoint": "POST /heartbeat/{agent_id}",
    },
]

# Optional: use Anthropic for fresh content
try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


def _get_client():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key or not ANTHROPIC_AVAILABLE:
        return None
    return Anthropic(api_key=api_key)


def _today_product() -> dict:
    """Get today's featured product based on day rotation."""
    import datetime
    day_of_year = datetime.datetime.now().timetuple().tm_yday
    return PRODUCT_ROTATION[day_of_year % len(PRODUCT_ROTATION)]


def generate_twitter_thread(angle: str, github_url: str, api_url: str) -> list[str] | None:
    """Generate a fresh Twitter thread using Claude. Returns list of tweets or None."""
    client = _get_client()
    if not client:
        return None

    product = _today_product()

    prompt = f"""You are a concise technical marketer. Write a 3-4 tweet thread promoting this specific product:

TODAY'S FOCUS PRODUCT: {product['name']}
Product details: {product['focus']}
Example endpoint: {product['endpoint']}

Full platform: {PRODUCT_CONFIG['name']} — also offers {', '.join(p['name'] for p in PRODUCT_ROTATION if p['name'] != product['name'])}
GitHub: {github_url}
Live API: {api_url}

Angle to focus on: {angle}

Key facts to weave in:
- 500K+ AI agent wallets exist on x402
- Stripe, Google, Coinbase all building agent payment rails
- Pricing: $0.005/signal, $0.01/scan, $0.01/risk
- Signals: RSI, ADX, MACD, volume ratio, composite BUY/SELL/HOLD
- Open source, MIT license

Rules:
- Each tweet MUST be under 270 characters (leave room for links)
- No hashtags, no emojis
- Sound like a builder sharing what they made, not a marketer
- Last tweet must include the GitHub URL
- Output ONLY the tweets, one per line, separated by ---"""

    try:
        msg = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = msg.content[0].text.strip()
        tweets = [t.strip() for t in raw.split("---") if t.strip()]

        # Enforce char limit
        valid = []
        for t in tweets:
            if len(t) > 280:
                t = t[:277] + "..."
            valid.append(t)

        return valid if len(valid) >= 2 else None
    except Exception as e:
        log.error(f"Claude thread generation failed: {e}")
        return None


def generate_devto_article(angle: str, github_url: str, api_url: str) -> dict | None:
    """Generate a fresh Dev.to article using Claude. Returns {title, body, tags} or None."""
    client = _get_client()
    if not client:
        return None

    product = _today_product()

    prompt = f"""Write a Dev.to article about this specific product:

TODAY'S FOCUS: {product['name']}
Details: {product['focus']}
Endpoint: {product['endpoint']}

Full platform: {PRODUCT_CONFIG['name']}
Tech stack: {', '.join(PRODUCT_CONFIG['tech_stack'])}
GitHub: {github_url}
Live API: {api_url}

Angle: {angle}

Target audience: developers building AI agents.

Features: {json.dumps(PRODUCT_CONFIG['features'])}
Pricing: {json.dumps(PRODUCT_CONFIG['pricing'])}

Rules:
- Title should be compelling, under 80 characters
- Article should be 400-600 words
- Include code snippets showing how to use the API
- Sound like a developer sharing a project, not selling
- End with the GitHub link
- Use markdown formatting

Output format:
TITLE: [your title]
TAGS: [comma-separated, max 4]
---
[article body in markdown]"""

    try:
        msg = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = msg.content[0].text.strip()

        # Parse
        lines = raw.split("\n")
        title = ""
        tags = []
        body_start = 0

        for i, line in enumerate(lines):
            if line.startswith("TITLE:"):
                title = line.replace("TITLE:", "").strip()
            elif line.startswith("TAGS:"):
                tags = [t.strip() for t in line.replace("TAGS:", "").split(",")][:4]
            elif line.strip() == "---":
                body_start = i + 1
                break

        body = "\n".join(lines[body_start:]).strip()

        if title and body and len(body) > 100:
            return {"title": title, "body": body, "tags": tags}
        return None
    except Exception as e:
        log.error(f"Claude article generation failed: {e}")
        return None


def generate_reddit_post(subreddit: str, github_url: str, api_url: str) -> dict | None:
    """Generate a fresh Reddit post using Claude. Returns {title, body} or None."""
    client = _get_client()
    if not client:
        return None

    product = _today_product()
    sub_config = PRODUCT_CONFIG.get("subreddits", {}).get(f"r/{subreddit}", {})
    angle = sub_config.get("angle", product["focus"])
    tone = sub_config.get("tone", "developer-friendly")

    prompt = f"""Write a Reddit post for r/{subreddit} about this specific product:

TODAY'S FOCUS: {product['name']}
Details: {product['focus']}
Endpoint: {product['endpoint']}

Full platform: {PRODUCT_CONFIG['name']}
GitHub: {github_url}
Live API: {api_url}

Angle: {angle}
Tone: {tone}

Pricing: {json.dumps(PRODUCT_CONFIG['pricing'])}
Features: {json.dumps(PRODUCT_CONFIG['features'])}

Rules:
- Title under 100 characters, compelling but not clickbait
- Body 150-300 words
- Sound like a real person sharing a project, not marketing
- Include the GitHub link
- Format for Reddit markdown
- No emojis

Output format:
TITLE: [your title]
---
[post body]"""

    try:
        msg = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = msg.content[0].text.strip()

        lines = raw.split("\n")
        title = ""
        body_start = 0

        for i, line in enumerate(lines):
            if line.startswith("TITLE:"):
                title = line.replace("TITLE:", "").strip()
            elif line.strip() == "---":
                body_start = i + 1
                break

        body = "\n".join(lines[body_start:]).strip()

        if title and body and len(body) > 50:
            return {"title": title, "body": body}
        return None
    except Exception as e:
        log.error(f"Claude Reddit post generation failed: {e}")
        return None


# Angles for rotation — the generator picks a fresh angle each cycle
TWITTER_ANGLES = [
    "Focus on x402 protocol and how the payment flow works",
    "Focus on the momentum scoring model (RSI + ADX + MACD + volume)",
    "Focus on the AI agent economy and why agents need payment rails",
    "Focus on the open-source aspect -- fork and build your own monetized API",
    "Focus on the NEW Agent Memory API -- agents can now persist state across sessions for $0.001/read",
    "Focus on the NEW Agent Identity system -- agents register, build reputation, verify each other",
    "Focus on the full stack: signals + memory + identity = complete agent infrastructure",
    "Focus on comparison: our 3 services vs building it yourself",
    "Focus on the scan endpoint -- agents can discover momentum setups automatically",
    "Focus on being one of the first live x402 implementations with 4 products",
    "Focus on the World Context API — AI agents don't know what time it is. This fixes it.",
    "Focus on how the Context API knows market hours, holidays, DST across 10 exchanges and 4 countries",
]

DEVTO_ANGLES = [
    "Tutorial: how to build a micropayment-gated API in 10 minutes",
    "The AI agent economy is here -- what developers need to build for it",
    "Why pay-per-call beats subscriptions for machine-to-machine commerce",
    "Building with x402: Coinbase's protocol for autonomous payments",
    "I built persistent memory for AI agents -- pay-per-read/write via x402",
    "Agent Identity and Reputation: the trust layer the AI economy needs",
    "From trading signals to full agent infrastructure -- our journey building 4 products",
    "AI agents don't know what time it is — I built an API that grounds them in reality",
    "World Context API: one call returns time, DST, market hours, holidays for any timezone",
]

REDDIT_ROTATION = [
    "algotrading",
    "LangChain",
    "autonomous_agents",
    "ethdev",
    "cryptocurrency",
    "artificial",
    "MachineLearning",
    "Python",
]
