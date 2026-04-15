"""
Ad content for all platforms. Rotates angles to avoid looking spammy.
"""


def _urls(github_repo: str, api_url: str) -> dict:
    return {
        "github": f"https://github.com/{github_repo}" if github_repo else "[github-url]",
        "api": api_url,
    }


# ---------------------------------------------------------------------------
# Twitter/X — threads posted via Forge TwitterPublisher
# ---------------------------------------------------------------------------
TWITTER_THREADS = [
    {
        "angle": "agent-payments",
        "tweets": [
            "I built a trading signal API designed for AI agents, not humans.\n\nNo signup. No API key. No subscription.\n\nYour agent pays $0.005 per call in USDC and gets momentum signals.\n\nHere's how it works:",
            "Agent calls GET /signal/NVDA\n\nGets HTTP 402 \"pay first\"\n\nAgent wallet auto-signs $0.005 USDC on Base L2\n\nRetries with payment proof\n\nGets signal data\n\nThe entire payment flow is automatic. No human touches anything.",
            "Signals include:\n- RSI (14) overbought/oversold\n- ADX (14) trend strength\n- MACD crossover + direction\n- Volume ratio vs 20-day avg\n- Composite BUY/SELL/HOLD + confidence score\n\nAll for half a cent per call.",
            "500K+ AI agent wallets already exist on x402.\n\nStripe, Google, and Coinbase are all building agent payment infrastructure.\n\nThis is the first trading signal API built natively for that world.\n\nOpen source: {github}",
        ],
    },
    {
        "angle": "x402-demo",
        "tweets": [
            "x402 is Coinbase's protocol for AI agent micropayments.\n\nI built the first trading signal API on it.\n\n$0.005/call. USDC on Base. No auth. No API keys.\n\nAgent shows up, pays, gets data. Here's a quick breakdown:",
            "The x402 flow:\n\n1. GET /signal/AAPL\n2. Server: HTTP 402 + payment details\n3. Agent signs USDC transfer\n4. Agent retries with payment header\n5. Gets signal JSON\n\n~10 lines of Python middleware to gate any endpoint behind micropayments.",
            "Endpoints:\n\n/signal/TICKER — $0.005 — BUY/SELL/HOLD + indicators\n/scan/momentum — $0.01 — top 10 setups\n/risk?tickers=X,Y — $0.01 — portfolio risk\n\nOpen source, self-hostable.\n\n{github}",
        ],
    },
    {
        "angle": "algo-trading",
        "tweets": [
            "If you're building AI trading agents, they all need the same thing: market signals.\n\nBut existing APIs need human signup, API keys, monthly billing.\n\nSo I built one where agents pay per call. Half a cent. USDC. No friction.",
            "What you get per call:\n\n- RSI, ADX, MACD, volume ratio\n- ATR as % of price\n- Composite score → BUY/SELL/HOLD\n- Confidence (0-1)\n- Current price + day change\n\nAll computed from 6 months of daily data. 5-min cache.",
            "Also has a momentum scanner:\n\nGET /scan/momentum\n\nScans 35 US equities, returns top 10 BUY setups ranked by confidence.\n\nAnd portfolio risk analysis:\n\nGET /risk?tickers=AAPL,NVDA,TSLA\n\nVol, drawdown, correlation, Sharpe.\n\n{github}",
        ],
    },
    {
        "angle": "agent-economy",
        "tweets": [
            "The AI agent economy is going to be bigger than the app economy.\n\nAgents need to pay each other. For data. For compute. For signals.\n\nI built a small piece of that: a trading signal API where agents pay per call in USDC.",
            "What makes this different from a normal API:\n\n- No signup or registration\n- No API keys to manage\n- No monthly billing\n- Pay exactly for what you use\n- Works 24/7, no human in the loop\n\nThis is how machine-to-machine commerce should work.",
            "Built with:\n- FastAPI (Python)\n- x402 protocol (Coinbase)\n- USDC on Base L2\n- yfinance for market data\n\nOpen source, MIT license. Fork it, adapt it to whatever data you want to sell to agents.\n\n{github}",
        ],
    },
]


# ---------------------------------------------------------------------------
# Dev.to — full articles
# ---------------------------------------------------------------------------
DEVTO_ARTICLES = [
    {
        "angle": "tutorial",
        "title": "I Built a Pay-Per-Call Trading Signal API for AI Agents",
        "tags": ["ai", "crypto", "python", "webdev"],
        "body": """
If you're building AI agents that trade, they need market signals. But most data APIs require human signup, API keys, and monthly subscriptions — none of which an autonomous agent can handle.

I built a trading signal API where AI agents pay per call using the x402 protocol (USDC micropayments on Base L2). No signup, no API keys. Agent shows up, pays half a cent, gets data.

## How x402 Works

x402 revives the HTTP 402 ("Payment Required") status code:

1. Agent calls `GET /signal/NVDA`
2. Server responds with HTTP 402 + payment instructions
3. Agent wallet signs a USDC transfer on Base L2
4. Agent retries with a payment proof header
5. Server verifies via Coinbase facilitator, returns data

The entire flow takes ~200ms.

## The Signal Engine

Each call returns a composite momentum score built from:

- **RSI (14)** — oversold/overbought detection
- **ADX (14)** — trend strength (>25 = strong trend)
- **MACD (12/26/9)** — crossover + direction
- **Volume ratio** — current vs 20-day average

Score maps to BUY (>=30), SELL (<=-30), or HOLD, with a confidence value from 0 to 1.

## Endpoints

| Endpoint | Price | Returns |
|---|---|---|
| `/signal/TICKER` | $0.005 | Single stock signal |
| `/scan/momentum` | $0.01 | Top 10 momentum setups |
| `/risk?tickers=X,Y` | $0.01 | Portfolio risk analysis |

## Stack

- FastAPI (sync endpoints for yfinance blocking I/O)
- x402 Python SDK with ASGI middleware
- LRU cache (200 entries, 5-min TTL)
- Deployed on Fly.io

Open source: {github}

If you're thinking about building services for the emerging AI agent economy, this is a template you can fork and adapt.
""",
    },
]


# ---------------------------------------------------------------------------
# Reddit — posts for specific subreddits
# ---------------------------------------------------------------------------
REDDIT_POSTS = [
    {
        "angle": "algotrading",
        "subreddits": ["algotrading"],
        "title": "Open-source momentum signal API with composite scoring (RSI + ADX + MACD + Volume)",
        "body": (
            "Built an API that computes momentum signals for US equities. "
            "Composite scoring from RSI(14), ADX(14), MACD(12/26/9), and volume ratio vs 20d average.\n\n"
            "Returns BUY/SELL/HOLD with confidence (0-1), plus all raw indicator values.\n\n"
            "Also has:\n"
            "- Momentum scanner (top 10 setups from 35+ tickers)\n"
            "- Portfolio risk endpoint (vol, drawdown, correlation, Sharpe)\n\n"
            "Pay-per-call via x402 ($0.005/call in USDC), or self-host for free.\n\n"
            "GitHub: {github}"
        ),
    },
    {
        "angle": "langchain",
        "subreddits": ["LangChain", "autonomous_agents"],
        "title": "Built a pay-per-call trading signal API for AI agents — no API keys needed",
        "body": (
            "If you're building AI trading agents, they need market signals. "
            "Most APIs require human signup and API keys your agent can't manage.\n\n"
            "I built an API where agents pay $0.005/call in USDC via x402 (Coinbase's machine payment protocol). "
            "No signup. No auth. Agent shows up, pays, gets data.\n\n"
            "Endpoints:\n"
            "- `/signal/{{ticker}}` — $0.005 — BUY/SELL/HOLD + RSI, ADX, MACD, volume, confidence\n"
            "- `/scan/momentum` — $0.01 — top 10 momentum setups\n"
            "- `/risk?tickers=X,Y,Z` — $0.01 — portfolio risk analysis\n\n"
            "Open source, MIT. GitHub: {github}\n"
            "Live: {api}/pricing"
        ),
    },
    {
        "angle": "crypto-dev",
        "subreddits": ["ethdev", "cryptocurrency"],
        "title": "x402 in practice: I built a micropayment-gated trading signal API",
        "body": (
            "Wanted to share a real implementation of x402 (Coinbase's HTTP 402 payment protocol).\n\n"
            "I built a trading signal API where AI agents pay per call in USDC on Base L2. "
            "The entire payment flow is automatic — agent gets 402, signs payment, retries, gets data.\n\n"
            "Stack: FastAPI + x402 Python SDK. ~10 lines of middleware to gate any endpoint behind micropayments.\n\n"
            "Signals: RSI, ADX, MACD, volume ratio, composite BUY/SELL/HOLD score.\n"
            "Pricing: $0.005 per signal call.\n\n"
            "Open source: {github}"
        ),
    },
    {
        "angle": "ai-general",
        "subreddits": ["artificial"],
        "title": "The AI agent economy is real — I built an API that AI agents pay for autonomously",
        "body": (
            "There are 500K+ AI agent wallets on x402. "
            "These agents need services they can pay for without human intermediaries.\n\n"
            "I built a trading signal API as a test case. Agents call an endpoint, "
            "pay $0.005 in USDC on Base L2, get momentum signals. "
            "No signup, no API key, no subscription. Pure machine-to-machine commerce.\n\n"
            "The x402 protocol (Coinbase) makes this trivial — ~10 lines of Python middleware.\n\n"
            "If you're thinking about building services for the agent economy, "
            "this is a template you can fork and adapt.\n\n"
            "Open source: {github}"
        ),
    },
]


# ---------------------------------------------------------------------------
# Discord
# ---------------------------------------------------------------------------
DISCORD_POSTS = [
    {
        "angle": "bittensor",
        "content": (
            "Built a trading signal API using x402 micropayments — agents pay $0.005/call in USDC "
            "for momentum signals (RSI, ADX, MACD, volume, composite score).\n\n"
            "Thinking about eventually building this into a subnet for decentralized signal generation. "
            "Right now proving out demand as a standalone API.\n\n"
            "Open source: {github}\nLive: {api}/pricing"
        ),
    },
    {
        "angle": "agent-builders",
        "content": (
            "If you're building trading agents that need market signals — "
            "I have a pay-per-call API. $0.005/call, USDC on Base, no API keys.\n\n"
            "Endpoints: /signal/{{ticker}}, /scan/momentum, /risk\nDocs: {github}"
        ),
    },
]


# ---------------------------------------------------------------------------
# GitHub — awesome-list PR submissions (one-time per list)
# ---------------------------------------------------------------------------
GITHUB_AWESOME_PRS = [
    {
        "repo": "xpaysh/awesome-x402",
        "entry": "- [Signal API](https://github.com/{github_repo}) - Momentum trading signals (RSI/ADX/MACD) for AI agents with x402 micropayments.",
        "body": "Adding Signal API — a trading signal API built for AI agents with x402 micropayments.\n\n- Endpoints: /signal/TICKER, /scan/momentum, /risk\n- $0.005/call in USDC on Base\n- FastAPI + x402 Python SDK\n- Open source, MIT\n\nRepo: {github}",
    },
]


# ---------------------------------------------------------------------------
# Dev.to — additional articles for rotation
# ---------------------------------------------------------------------------
DEVTO_ARTICLES.append({
    "angle": "agent-economy",
    "title": "The AI Agent Economy Needs Payment Rails — Here's What I Built",
    "tags": ["ai", "web3", "python", "startup"],
    "body": """
500K+ AI agent wallets exist on x402. Stripe launched machine payment protocols. Google announced AP2. The infrastructure for autonomous AI commerce is being built right now.

I wanted to test the thesis: can you build a service that AI agents pay for, with zero human intermediaries?

## The Experiment

I built a trading signal API. Agents call an endpoint, pay $0.005 in USDC on Base L2 via x402, and get back momentum signals (RSI, ADX, MACD, volume, composite score).

No signup. No API keys. No subscriptions. No humans in the loop.

## What I Learned

**x402 makes this trivial.** About 10 lines of FastAPI middleware to gate any endpoint behind micropayments. The Coinbase facilitator handles verification and settlement.

**The real bottleneck is discovery.** How does an agent find your API? Right now, a human developer has to wire it in. True agent-to-agent discovery (where Agent A searches for "trading signals" and autonomously starts paying Agent B) is 12-18 months away.

**Pricing for machines is different.** Agents don't care about $9.99/month vs $12.99/month. They care about cost-per-call. Sub-cent micropayments change the economics entirely.

## The Stack

- FastAPI with sync endpoints (yfinance blocks I/O)
- x402 Python SDK with ASGI middleware
- USDC on Base L2 (sub-cent gas costs)
- LRU cache, 5-min TTL
- Deployed on Fly.io (~$0/month)

## What's Next

If this gets traction, the next step is a Bittensor subnet — decentralize the signal generation so miners compete to produce better signals, validators score against actual market performance.

Open source: {github}
""",
})


def format_content(template: str, github_repo: str, api_url: str) -> str:
    urls = _urls(github_repo, api_url)
    return template.format(github=urls["github"], api=urls["api"])
