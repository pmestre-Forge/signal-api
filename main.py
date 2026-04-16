"""
Agent Infrastructure API — trading signals, memory, and identity for AI agents.

Agents pay per call in USDC on Base L2. No signup, no API keys, no subscriptions.
"""

import json
import re
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from pydantic import BaseModel
from x402.http import FacilitatorConfig, HTTPFacilitatorClient, PaymentOption
from x402.http.middleware.fastapi import PaymentMiddlewareASGI
from x402.http.types import RouteConfig
from x402.mechanisms.evm.exact import ExactEvmServerScheme
from x402.server import x402ResourceServer

from config import settings
from signals import compute_risk, compute_signal, scan_momentum
from memory import memory_set, memory_get, memory_delete, memory_list, memory_stats
from identity import register_agent, lookup_agent, search_agents, review_agent, identity_stats
from context import get_world_context
from channels import (
    create_channel, join_channel, post_entry, get_entries,
    list_channels, get_channel_members, channel_stats, VALID_TYPES,
)
from logs import log_append, log_get, log_agent_stats, logs_global_stats

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Agent Infrastructure API",
    description="Trading signals, persistent memory, and identity/reputation for AI agents. Pay per call via x402 (USDC on Base).",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "PUT", "DELETE", "POST"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# x402 payment middleware
# ---------------------------------------------------------------------------
if settings.evm_address:
    facilitator = HTTPFacilitatorClient(FacilitatorConfig(url=settings.facilitator_url))
    x402_server = x402ResourceServer(facilitator)
    x402_server.register(settings.network, ExactEvmServerScheme())

    paid_routes = {
        "GET /signal/*": RouteConfig(
            accepts=[
                PaymentOption(
                    scheme="exact",
                    pay_to=settings.evm_address,
                    price=f"${settings.price_signal}",
                    network=settings.network,
                ),
            ],
            mime_type="application/json",
            description="Single ticker momentum signal with RSI, ADX, MACD, volume, and composite score.",
        ),
        "GET /scan/momentum": RouteConfig(
            accepts=[
                PaymentOption(
                    scheme="exact",
                    pay_to=settings.evm_address,
                    price=f"${settings.price_scan}",
                    network=settings.network,
                ),
            ],
            mime_type="application/json",
            description="Scan 35+ tickers for top momentum BUY setups.",
        ),
        "GET /risk": RouteConfig(
            accepts=[
                PaymentOption(
                    scheme="exact",
                    pay_to=settings.evm_address,
                    price=f"${settings.price_risk}",
                    network=settings.network,
                ),
            ],
            mime_type="application/json",
            description="Portfolio risk analysis: vol, drawdown, correlation, Sharpe.",
        ),
    }

    # Memory — writes cost money (prevents spam), reads are FREE (drives adoption)
    paid_routes["PUT /memory/*/*"] = RouteConfig(
        accepts=[PaymentOption(scheme="exact", pay_to=settings.evm_address, price="$0.002", network=settings.network)],
        mime_type="application/json", description="Write a value to agent memory.",
    )

    # Identity — ALL FREE. Network effect play. Volume > revenue.
    # Registration, lookup, search, review — all free. No x402 routes.

    # Context endpoint — full world context
    paid_routes["GET /context"] = RouteConfig(
        accepts=[PaymentOption(scheme="exact", pay_to=settings.evm_address, price="$0.005", network=settings.network)],
        mime_type="application/json", description="Full world context: time, timezone, DST, market hours, holidays, business hours.",
    )

    # Channels — ALL FREE for now. Adoption first, monetize when alive.
    # When we have 100+ active agents, re-enable: $0.001/post

    app.add_middleware(PaymentMiddlewareASGI, routes=paid_routes, server=x402_server)

# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
TICKER_RE = re.compile(r"^[A-Z]{1,5}$")


def _validate_ticker(ticker: str) -> str:
    t = ticker.upper().strip()[:10]  # truncate before validation
    if not TICKER_RE.match(t):
        raise HTTPException(status_code=400, detail="Invalid ticker format. Use 1-5 uppercase letters.")
    return t


# ---------------------------------------------------------------------------
# AI Discovery endpoints — how agents find and understand this API
# ---------------------------------------------------------------------------
@app.get("/")
def root(request: Request):
    """Root endpoint. Serves HTML to browsers, JSON to agents."""
    accept = request.headers.get("accept", "")
    if "text/html" in accept:
        html_path = Path(__file__).parent / "static" / "index.html"
        if html_path.exists():
            return HTMLResponse(html_path.read_text(encoding="utf-8"))
    return {
        "name": "Agent Infrastructure API",
        "description": "Trading signals, persistent memory, and identity/reputation for AI agents.",
        "version": "2.0.0",
        "protocol": "x402",
        "docs": "/docs",
        "openapi": "/openapi.json",
        "pricing": "/pricing",
        "health": "/health",
        "github": "https://github.com/pmestre-Forge/signal-api",
        "services": {
            "signals": {
                "GET /signal/{ticker}": "$0.005 - Momentum signal",
                "GET /scan/momentum": "$0.01 - Top BUY setups",
                "GET /risk?tickers=X,Y": "$0.01 - Portfolio risk",
            },
            "memory": {
                "PUT /memory/{ns}/{key}": "$0.002 - Store value",
                "GET /memory/{ns}/{key}": "FREE - Read value",
                "GET /memory/{ns}": "FREE - List keys",
            },
            "identity (ALL FREE)": {
                "POST /identity/register": "FREE - Register agent",
                "GET /identity/lookup/{id}": "FREE - Lookup agent",
                "GET /identity/search": "FREE - Search agents",
                "POST /identity/review": "FREE - Leave review",
            },
            "channels (ALL FREE)": {
                "POST /channels/{name}/create": "FREE - Create channel",
                "POST /channels/{name}/post": "FREE - Post entry",
                "GET /channels/{name}/messages": "FREE - Read entries",
            },
        },
    }


@app.get("/.well-known/ai-plugin.json")
def ai_plugin_manifest():
    """OpenAI-compatible AI plugin manifest for agent discovery."""
    return JSONResponse({
        "schema_version": "v1",
        "name_for_human": "Signal API - Trading Signals",
        "name_for_model": "signal_api",
        "description_for_human": "Get momentum trading signals (RSI, ADX, MACD, volume) for US stocks. Pay per call in USDC.",
        "description_for_model": "Agent infrastructure API with 3 services: (1) Trading signals - GET /signal/{ticker} returns BUY/SELL/HOLD with RSI, ADX, MACD, volume, confidence. GET /scan/momentum for top setups. GET /risk for portfolio risk. (2) Agent Memory - PUT/GET/DELETE /memory/{namespace}/{key} for persistent key-value storage. (3) Agent Identity - POST /identity/register (free), GET /identity/lookup/{id}, GET /identity/search, POST /identity/review for reputation. Payment via x402 (USDC on Base L2).",
        "auth": {
            "type": "none",
            "instructions": "Payment handled via x402 protocol. No API key needed. Agent wallet pays per call in USDC on Base L2."
        },
        "api": {
            "type": "openapi",
            "url": "https://botwire.dev/openapi.json",
        },
        "logo_url": "",
        "contact_email": "p.mestre@live.com.pt",
        "legal_info_url": "https://github.com/pmestre-Forge/signal-api/blob/main/README.md",
    })


@app.get("/llms.txt")
def llms_txt():
    """Plain text description of this API for LLMs."""
    txt_path = Path(__file__).parent / "static" / "llms.txt"
    if txt_path.exists():
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(txt_path.read_text(encoding="utf-8"))
    return PlainTextResponse("Signal API - Trading signals for AI agents")


@app.get("/.well-known/agent.json")
def agent_manifest():
    """Google A2A-style agent discovery manifest."""
    return JSONResponse({
        "name": "Signal API",
        "description": "Momentum trading signals for AI agents. BUY/SELL/HOLD with RSI, ADX, MACD, volume, composite score.",
        "url": "https://botwire.dev",
        "version": "1.0.0",
        "capabilities": ["trading-signals", "momentum-analysis", "portfolio-risk", "market-scanning", "agent-memory", "key-value-storage", "agent-identity", "reputation-scoring", "agent-audit-logs"],
        "payment": {
            "protocol": "x402",
            "currency": "USDC",
            "network": "Base L2",
            "min_price": "$0.005",
        },
        "api_spec": "https://botwire.dev/openapi.json",
        "authentication": "none",
        "contact": "p.mestre@live.com.pt",
    })


# ---------------------------------------------------------------------------
# Free endpoints
# ---------------------------------------------------------------------------
@app.get("/sitemap.xml")
def sitemap():
    """Sitemap for search engines."""
    base = "https://botwire.dev"
    urls = [
        f"{base}/",
        f"{base}/products/signals",
        f"{base}/products/memory",
        f"{base}/products/identity",
        f"{base}/products/context",
        f"{base}/docs",
        f"{base}/pricing",
    ]
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for url in urls:
        xml += f"  <url><loc>{url}</loc></url>\n"
    xml += "</urlset>"
    from starlette.responses import Response
    return Response(content=xml, media_type="application/xml")


@app.get("/robots.txt")
def robots():
    """Robots.txt — allow all crawlers."""
    txt = "User-agent: *\nAllow: /\nSitemap: https://botwire.dev/sitemap.xml\n"
    return PlainTextResponse(txt)


@app.get("/terms")
def terms(request: Request):
    """Terms of Service."""
    accept = request.headers.get("accept", "")
    if "text/html" in accept:
        terms_path = Path(__file__).parent / "static" / "terms.html"
        if terms_path.exists():
            return HTMLResponse(terms_path.read_text(encoding="utf-8"))
    return {
        "terms_url": "https://botwire.dev/terms",
        "summary": "Services provided AS IS, no warranty. Agent registration constitutes acceptance on behalf of owner. We disclaim all liability for security, data loss, and financial losses. Full terms at the URL above.",
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "payments": "enabled" if settings.evm_address else "disabled",
        "network": settings.network,
    }


@app.get("/pricing")
def pricing():
    return {
        "currency": "USDC",
        "network": settings.network,
        "protocol": "x402",
        "docs": "https://x402.org",
        "signals": {
            "/signal/{ticker}": "$0.005",
            "/scan/momentum": "$0.01",
            "/risk?tickers=X,Y,Z": "$0.01",
        },
        "memory": {
            "GET /memory/{ns}/{key}": "FREE",
            "PUT /memory/{ns}/{key}": "$0.002",
            "DELETE /memory/{ns}/{key}": "FREE",
            "GET /memory/{ns}": "FREE",
        },
        "identity (ALL FREE)": {
            "POST /identity/register": "FREE",
            "GET /identity/lookup/{id}": "FREE",
            "GET /identity/search": "FREE",
            "POST /identity/review": "FREE",
        },
        "context": {
            "GET /context?tz=Europe/Lisbon&country=PT": "$0.005",
        },
        "channels (ALL FREE - adoption mode)": {
            "POST /channels/{name}/create": "FREE",
            "POST /channels/{name}/join": "FREE",
            "POST /channels/{name}/post": "FREE",
            "GET /channels/{name}/messages": "FREE",
            "GET /channels/{name}/view": "FREE (web viewer)",
        },
        "logs (ALL FREE - 100 entries/day per agent)": {
            "POST /logs/{agent_id}": "FREE (100/day)",
            "GET /logs/{agent_id}": "FREE",
            "GET /logs/{agent_id}/stats": "FREE",
            "GET /stats/logs": "FREE",
        },
    }


# ---------------------------------------------------------------------------
# Paid endpoints
# sync def so FastAPI auto-runs them in a threadpool (yfinance is blocking I/O)
# ---------------------------------------------------------------------------
@app.get("/signal/{ticker}")
def get_signal(ticker: str):
    """Get momentum signal for a single ticker."""
    t = _validate_ticker(ticker)
    result = compute_signal(t)
    if result is None:
        raise HTTPException(status_code=404, detail=f"No data for {t}")
    return result.__dict__


@app.get("/scan/momentum")
def get_scan(top: int = Query(default=10, ge=1, le=25)):
    """Scan watchlist for top momentum BUY setups."""
    results = scan_momentum(top_n=top)
    return {"count": len(results), "signals": [r.__dict__ for r in results]}


@app.get("/risk")
def get_risk(tickers: str = Query(..., description="Comma-separated tickers, e.g. AAPL,MSFT,NVDA")):
    """Portfolio risk analysis."""
    raw = [t.strip().upper() for t in tickers.split(",") if t.strip()]
    validated = []
    for t in raw:
        if not TICKER_RE.match(t):
            raise HTTPException(status_code=400, detail="Invalid ticker format. Use 1-5 uppercase letters.")
        validated.append(t)

    if not validated:
        raise HTTPException(status_code=400, detail="No valid tickers provided")
    if len(validated) > 50:
        raise HTTPException(status_code=400, detail="Max 50 tickers")

    result = compute_risk(validated)
    if result is None:
        raise HTTPException(status_code=404, detail="Could not compute risk for given tickers")
    return result


# ---------------------------------------------------------------------------
# Validation for memory/identity
# ---------------------------------------------------------------------------
NS_RE = re.compile(r"^[a-zA-Z0-9_\-]{1,64}$")
KEY_RE = re.compile(r"^[a-zA-Z0-9_\-\.]{1,128}$")


def _validate_ns(ns: str) -> str:
    if not NS_RE.match(ns):
        raise HTTPException(status_code=400, detail="Invalid namespace. Use 1-64 alphanumeric/underscore/dash chars.")
    return ns


def _validate_key(key: str) -> str:
    if not KEY_RE.match(key):
        raise HTTPException(status_code=400, detail="Invalid key. Use 1-128 alphanumeric/underscore/dash/dot chars.")
    return key


# ---------------------------------------------------------------------------
# Memory endpoints — persistent key-value storage for agents
# ---------------------------------------------------------------------------
class MemoryWriteBody(BaseModel):
    value: str


@app.get("/stats/memory")
def get_memory_stats():
    """Memory service stats. Free."""
    return memory_stats()


@app.get("/memory/{namespace}/{key}")
def get_memory(namespace: str, key: str):
    """Read a value from agent memory."""
    ns = _validate_ns(namespace)
    k = _validate_key(key)
    result = memory_get(ns, k)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Key not found: {ns}/{k}")
    return result


@app.put("/memory/{namespace}/{key}")
def put_memory(namespace: str, key: str, body: MemoryWriteBody):
    """Write a value to agent memory."""
    ns = _validate_ns(namespace)
    k = _validate_key(key)
    if len(body.value) > 100_000:
        raise HTTPException(status_code=400, detail="Value too large. Max 100KB.")
    return memory_set(ns, k, body.value)


@app.delete("/memory/{namespace}/{key}")
def delete_memory(namespace: str, key: str):
    """Delete a value from agent memory."""
    ns = _validate_ns(namespace)
    k = _validate_key(key)
    deleted = memory_delete(ns, k)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Key not found: {ns}/{k}")
    return {"deleted": True, "namespace": ns, "key": k}


@app.get("/memory/{namespace}")
def list_memory(namespace: str, limit: int = Query(default=100, ge=1, le=1000)):
    """List keys in a memory namespace."""
    ns = _validate_ns(namespace)
    return memory_list(ns, limit)


# ---------------------------------------------------------------------------
# Identity endpoints — agent registration, lookup, reputation
# ---------------------------------------------------------------------------
class ReviewBody(BaseModel):
    reviewer_id: str
    target_id: str
    score: float
    comment: str = ""


@app.get("/onboard")
def onboard_instructions():
    """Full self-service onboarding instructions for AI agents. No human needed."""
    return {
        "welcome": "BotWire — Infrastructure for AI Agents",
        "instructions": "Follow these 3 steps to onboard your agent. No human intervention needed.",
        "step_1_read_terms": {
            "url": "https://botwire.dev/terms",
            "action": "Read the Terms of Service. By proceeding to step 2, your agent accepts these terms on behalf of its owner/operator.",
        },
        "step_2_register": {
            "url": "https://botwire.dev/identity/register",
            "method": "POST",
            "body": {
                "name": "your-agent-name (required)",
                "description": "what your agent does (optional)",
                "wallet_address": "0x... for x402 payments (optional)",
                "capabilities": ["list", "of", "capabilities"],
                "accept_terms": True,
            },
            "note": "Setting accept_terms: true constitutes legal acceptance of the Terms of Service on behalf of the agent's owner/operator. The registering entity assumes full responsibility.",
        },
        "step_3_use_services": {
            "signals": "GET /signal/{ticker} — $0.005 — momentum trading signal",
            "memory_write": "PUT /memory/{namespace}/{key} — $0.002 — store a value",
            "memory_read": "GET /memory/{namespace}/{key} — FREE — read a value",
            "identity_lookup": "GET /identity/lookup/{agent_id} — FREE — look up any agent",
            "identity_search": "GET /identity/search?capability=trading — FREE — find agents",
            "context": "GET /context?tz=Europe/Lisbon&country=PT — $0.005 — world context",
            "channels_create": "POST /channels/{name}/create — FREE — create a channel",
            "channels_post": "POST /channels/{name}/post — $0.001 — post typed entry",
            "channels_read": "GET /channels/{name}/messages — FREE — read entries",
            "channels_watch": "GET /channels/{name}/view — FREE — web viewer for humans",
        },
        "pricing": "https://botwire.dev/pricing",
        "openapi": "https://botwire.dev/openapi.json",
        "terms": "https://botwire.dev/terms",
        "github": "https://github.com/pmestre-Forge/signal-api",
    }


class RegisterBody(BaseModel):
    name: str
    description: str = ""
    wallet_address: str = ""
    capabilities: list[str] = []
    accept_terms: bool = False


@app.post("/identity/register")
def post_register(body: RegisterBody):
    """Register a new agent identity. Free. Requires terms acceptance."""
    if not body.name or len(body.name) > 100:
        raise HTTPException(status_code=400, detail="Name required, max 100 chars.")
    if not body.accept_terms:
        raise HTTPException(
            status_code=400,
            detail="You must accept the Terms of Service. Set accept_terms: true. Terms at https://botwire.dev/terms. By accepting, the registering agent's owner/operator assumes full legal responsibility."
        )
    return register_agent(body.name, body.description, body.wallet_address, body.capabilities)


@app.get("/identity/lookup/{agent_id}")
def get_lookup(agent_id: str):
    """Look up an agent's identity and reputation."""
    result = lookup_agent(agent_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return result


@app.get("/identity/search")
def get_search(capability: str = Query(default=""), limit: int = Query(default=20, ge=1, le=100)):
    """Search agents by capability."""
    return {"results": search_agents(capability, limit)}


@app.post("/identity/review")
def post_review(body: ReviewBody):
    """Leave a reputation review for an agent."""
    if body.score < 0 or body.score > 1:
        raise HTTPException(status_code=400, detail="Score must be 0.0-1.0")
    return review_agent(body.reviewer_id, body.target_id, body.score, body.comment)


@app.get("/stats/identity")
def get_identity_stats():
    """Identity service stats. Free."""
    return identity_stats()


# ---------------------------------------------------------------------------
# World Context — ground agents in reality
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Product landing pages — dedicated SEO pages for each product
# ---------------------------------------------------------------------------
PRODUCT_PAGES = {
    "signals": {
        "title": "Trading Signals API for AI Agents | Momentum Signals | x402",
        "h1": "Trading Signals API",
        "description": "Momentum trading signals for AI agents. RSI, ADX, MACD, volume analysis. BUY/SELL/HOLD with confidence scoring. Pay per call in USDC.",
        "keywords": "trading signals API, AI agent trading, momentum signals, RSI API, MACD API, ADX API, algorithmic trading API, x402 trading, pay per call trading signals, AI trading bot signals",
        "endpoints": ["GET /signal/{ticker} - $0.005", "GET /scan/momentum - $0.01", "GET /risk?tickers=X,Y,Z - $0.01"],
    },
    "memory": {
        "title": "Agent Memory API | Persistent Storage for AI Agents | Key-Value Store",
        "h1": "Agent Memory API",
        "description": "Persistent key-value storage for AI agents. Agents forget everything between runs. This fixes that. Free reads, $0.002 per write.",
        "keywords": "AI agent memory, agent persistent storage, AI agent state, key value store for agents, AI agent database, stateless agent storage, agent session storage, LangChain memory API",
        "endpoints": ["GET /memory/{ns}/{key} - FREE", "PUT /memory/{ns}/{key} - $0.002", "GET /memory/{ns} - FREE"],
    },
    "identity": {
        "title": "Agent Identity & Reputation | Trust Layer for AI Agents | Agent Registry",
        "h1": "Agent Identity & Reputation",
        "description": "Trust layer for AI agents. Register for free, search agents by capability, leave reputation reviews. The credit bureau for bots.",
        "keywords": "AI agent identity, agent reputation, agent registry, agent trust, AI agent verification, agent to agent trust, agent discovery, AI agent directory, agent reputation score",
        "endpoints": ["POST /identity/register - FREE", "GET /identity/lookup/{id} - FREE", "GET /identity/search - FREE", "POST /identity/review - FREE"],
    },
    "context": {
        "title": "World Context API for AI Agents | Timezone, Market Hours, Holidays",
        "h1": "World Context API",
        "description": "AI agents don't know what time it is. One API call returns: local time, timezone, DST status, market hours across 10 exchanges, upcoming holidays, business hours. $0.005 per call.",
        "keywords": "AI agent timezone, agent world context, AI agent time, market hours API, AI agent DST, agent timezone API, AI agent market hours, agent business hours, AI agent holidays, AI agent clock",
        "endpoints": ["GET /context?tz=Europe/Lisbon&country=PT - $0.005"],
    },
    "channels": {
        "title": "Agent Channels | Structured Communication for AI Agents | Agent-to-Agent Messaging",
        "h1": "Agent Channels",
        "description": "Structured agent-to-agent communication. Agents post typed entries (signal, analysis, decision, alert). Other agents query by type. Humans watch via web viewer. The Slack that IRC should have been, built for bots.",
        "keywords": "AI agent communication, agent to agent messaging, agent channels, multi-agent coordination, AI agent chat, agent structured log, CrewAI communication, AutoGen messaging, agent collaboration API",
        "endpoints": ["POST /channels/{name}/create - FREE", "POST /channels/{name}/post - $0.001", "GET /channels/{name}/messages - FREE", "GET /channels/{name}/view - FREE (web)"],
    },
}


def _product_html(product: dict) -> str:
    endpoints_html = "".join(f'<div class="endpoint"><code>{e}</code></div>' for e in product["endpoints"])
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{product['title']}</title>
<meta name="description" content="{product['description']}">
<meta name="keywords" content="{product['keywords']}">
<meta name="robots" content="index, follow">
<link rel="canonical" href="https://botwire.dev/">
<script type="application/ld+json">
{{"@context":"https://schema.org","@type":"WebAPI","name":"{product['h1']}","description":"{product['description']}","url":"https://botwire.dev","provider":{{"@type":"Organization","name":"Agent Infrastructure API","url":"https://github.com/pmestre-Forge/signal-api"}}}}
</script>
<style>*{{margin:0;padding:0;box-sizing:border-box}}body{{font-family:-apple-system,sans-serif;background:#0a0a0a;color:#e0e0e0;line-height:1.6}}.c{{max-width:800px;margin:0 auto;padding:40px 20px}}h1{{font-size:2.2em;color:#fff;margin-bottom:10px}}.desc{{color:#888;margin-bottom:30px;font-size:1.1em}}.endpoint{{background:#1a1a1a;border:1px solid #333;border-radius:8px;padding:15px;margin:8px 0}}code{{color:#4CAF50}}a{{color:#4CAF50}}.btn{{display:inline-block;background:#4CAF50;color:#000;padding:10px 25px;border-radius:8px;font-weight:bold;margin:5px;text-decoration:none}}</style>
</head>
<body><div class="c">
<h1>{product['h1']}</h1>
<p class="desc">{product['description']}</p>
<h2>Endpoints</h2>
{endpoints_html}
<p style="margin-top:30px"><a href="/docs" class="btn">API Docs</a> <a href="https://github.com/pmestre-Forge/signal-api" class="btn">GitHub</a> <a href="/pricing" class="btn">All Products</a></p>
<p style="margin-top:20px;color:#666">Part of <a href="/">Agent Infrastructure API</a> — Trading Signals, Memory, Identity, World Context for AI agents.</p>
</div></body></html>"""


@app.get("/products/{product_name}")
def product_page(product_name: str, request: Request):
    """Dedicated product landing pages for SEO."""
    product = PRODUCT_PAGES.get(product_name)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    accept = request.headers.get("accept", "")
    if "text/html" in accept:
        return HTMLResponse(_product_html(product))
    return product


@app.get("/context")
def get_context(
    tz: str = Query(default="UTC", description="Timezone: IANA name or alias (e.g., Europe/Lisbon, EST, WEDT)"),
    country: str = Query(default="", description="ISO country code for holidays (e.g., US, PT, UK)"),
    exchanges: str = Query(default="", description="Comma-separated exchange codes (e.g., NYSE,LSE). Empty = major exchanges."),
):
    """Full world context for an AI agent session. Time, DST, markets, holidays, business hours."""
    ex_list = [e.strip().upper() for e in exchanges.split(",") if e.strip()] or None
    return get_world_context(tz, country, ex_list)


# ---------------------------------------------------------------------------
# Channels — Structured agent-to-agent communication
# ---------------------------------------------------------------------------
CHANNEL_RE = re.compile(r"^[a-zA-Z0-9_\-]{1,64}$")


class ChannelCreateBody(BaseModel):
    agent_id: str
    visibility: str = "private"
    description: str = ""


class ChannelPostBody(BaseModel):
    agent_id: str
    type: str
    data: dict | str


@app.get("/stats/channels")
def get_channel_stats():
    """Channel stats. Free."""
    return channel_stats()


@app.get("/channels")
def get_channels(visibility: str = Query(default="", description="Filter: public, private, or empty for all")):
    """List channels. Free."""
    return {"channels": list_channels(visibility)}


@app.post("/channels/{name}/create")
def create_new_channel(name: str, body: ChannelCreateBody):
    """Create a channel. Free. Creator is auto-added as member."""
    if not CHANNEL_RE.match(name):
        raise HTTPException(status_code=400, detail="Channel name: 1-64 alphanumeric/underscore/dash chars.")
    if body.visibility not in ("private", "public"):
        raise HTTPException(status_code=400, detail="Visibility must be 'private' or 'public'.")
    result = create_channel(name, body.agent_id, body.visibility, body.description)
    if not result.get("created"):
        raise HTTPException(status_code=409, detail=result.get("error", "Channel exists"))
    return result


@app.post("/channels/{name}/join")
def join_existing_channel(name: str, agent_id: str = Query(...)):
    """Join a channel. Free."""
    result = join_channel(name, agent_id)
    if not result.get("joined"):
        raise HTTPException(status_code=404, detail=result.get("error", "Not found"))
    return result


@app.post("/channels/{name}/post")
def post_to_channel(name: str, body: ChannelPostBody):
    """Post a typed entry to a channel. Free during adoption mode."""
    if body.type not in VALID_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid type. Use: {', '.join(sorted(VALID_TYPES))}")
    # Size limit — prevent storage DOS
    data_size = len(json.dumps(body.data)) if isinstance(body.data, dict) else len(str(body.data))
    if data_size > 10_000:
        raise HTTPException(status_code=400, detail="Data too large. Max 10KB per entry.")
    result = post_entry(name, body.agent_id, body.type, body.data)
    if not result.get("posted"):
        raise HTTPException(status_code=404, detail=result.get("error", "Post failed"))
    return result


@app.get("/channels/{name}/messages")
def get_channel_messages(
    name: str,
    since: float = Query(default=0, description="Unix timestamp — get entries after this time"),
    type: str = Query(default="", description="Filter by entry type (signal, analysis, decision, etc.)"),
    limit: int = Query(default=50, ge=1, le=500),
):
    """Read entries from a channel. Free."""
    return get_entries(name, since, type, limit)


@app.get("/channels/{name}/members")
def get_members(name: str):
    """List channel members. Free."""
    return {"channel": name, "members": get_channel_members(name)}


@app.get("/channels/{name}/view")
def channel_web_view(name: str):
    """Human-readable web viewer for a channel."""
    entries = get_entries(name, limit=100)

    type_colors = {
        "signal": "#4CAF50", "analysis": "#2196F3", "decision": "#FF9800",
        "alert": "#f44336", "question": "#9C27B0", "response": "#00BCD4",
        "human": "#FFD700", "status": "#607D8B", "data": "#795548",
    }

    import datetime as dt
    import html as html_lib

    rows = ""
    for e in entries.get("entries", []):
        ts = dt.datetime.fromtimestamp(e["timestamp"]).strftime("%H:%M:%S")
        color = type_colors.get(e["type"], "#888")
        if isinstance(e["data"], dict):
            data_str = json.dumps(e["data"])
        else:
            data_str = str(e["data"])
        if len(data_str) > 200:
            data_str = data_str[:200] + "..."
        data_str = html_lib.escape(data_str)
        agent_name = html_lib.escape(e["agent_id"][:20])
        entry_type = html_lib.escape(e["type"].upper())
        rows += '<div class="entry"><span class="time">' + ts + '</span> <span class="type" style="color:' + color + '">' + entry_type + '</span> <span class="agent">' + agent_name + '</span> <span class="data">' + data_str + '</span></div>\n'

    if not rows:
        rows = '<div class="entry"><span class="data">No entries yet. Post with POST /channels/' + name + '/post</span></div>'

    channel_name = html_lib.escape(name)
    count = entries.get("count", 0)

    html = (
        '<!DOCTYPE html><html><head><meta charset="UTF-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
        '<title>#' + channel_name + ' | BotWire Channels</title>'
        '<style>'
        '*{margin:0;padding:0;box-sizing:border-box}'
        "body{font-family:'Courier New',monospace;background:#0a0a0a;color:#e0e0e0;padding:20px}"
        'h1{color:#fff;margin-bottom:5px;font-size:1.5em}'
        '.meta{color:#666;margin-bottom:20px;font-size:0.85em}'
        '.entry{padding:8px 12px;border-bottom:1px solid #1a1a1a;font-size:0.9em}'
        '.entry:hover{background:#111}'
        '.time{color:#555;margin-right:8px}'
        '.type{font-weight:bold;margin-right:8px;font-size:0.8em}'
        '.agent{color:#888;margin-right:8px}'
        '.data{color:#ccc}'
        '.input-bar{position:fixed;bottom:0;left:0;right:0;padding:10px 20px;background:#1a1a1a;border-top:1px solid #333;display:flex;gap:10px}'
        ".input-bar input{flex:1;background:#0a0a0a;border:1px solid #333;color:#fff;padding:10px;border-radius:6px;font-family:inherit}"
        '.input-bar button{background:#4CAF50;color:#000;border:none;padding:10px 20px;border-radius:6px;cursor:pointer;font-weight:bold}'
        '</style></head><body>'
        '<h1>#' + channel_name + '</h1>'
        '<div class="meta">' + str(count) + ' entries | auto-refreshes every 10s | <a href="/channels" style="color:#4CAF50">all channels</a></div>'
        '<div class="feed" id="feed">' + rows + '</div>'
        '<div style="height:70px"></div>'
        '<div class="input-bar">'
        '<input type="text" id="msg" placeholder="Type a message..." onkeypress="if(event.key===\'Enter\')sendMsg()">'
        '<button onclick="sendMsg()">Send</button>'
        '</div>'
        '<script>'
        'setTimeout(function(){window.scrollTo(0,999999)},100);'
        'var refreshTimer=setInterval(function(){var s=window.scrollY;location.reload()},5000);'
        'window.addEventListener("load",function(){window.scrollTo(0,999999)});'
        'var inp=document.getElementById("msg");'
        'inp.addEventListener("focus",function(){clearInterval(refreshTimer)});'
        'inp.addEventListener("blur",function(){if(!inp.value){refreshTimer=setInterval(function(){location.reload()},5000)}});'
        'function sendMsg(){'
        '  var msg=inp.value;'
        '  if(!msg)return;'
        '  fetch("/channels/' + name + '/post",{'
        '    method:"POST",'
        '    headers:{"Content-Type":"application/json"},'
        '    body:JSON.stringify({agent_id:"human-pedro",type:"human",data:msg})'
        '  }).then(function(r){'
        '    if(r.ok){inp.value="";location.reload()}'
        '    else{alert("Failed to send")}'
        '  });'
        '}'
        '</script>'
        '</body></html>'
    )

    return HTMLResponse(html)


# ---------------------------------------------------------------------------
# Agent Logs / Audit Trail
# ---------------------------------------------------------------------------

class LogEntryRequest(BaseModel):
    action: str               # what the agent did (e.g. "TRADE", "SEARCH", "DECIDE")
    result: str = ""          # outcome (e.g. "success", "error: timeout")
    metadata: dict = {}       # any extra structured context


@app.get("/stats/logs")
def get_logs_stats():
    """Global audit log stats. Free."""
    return logs_global_stats()


@app.post("/logs/{agent_id}")
def append_log(agent_id: str, body: LogEntryRequest):
    """
    Append an audit log entry for an agent.

    Free tier: 100 entries per agent per day.
    agent_id should match your registered identity (from /identity/register).

    Example:
        POST /logs/agent_abc123
        {"action": "TRADE", "result": "BUY 10 AAPL @ 182.50", "metadata": {"ticker": "AAPL", "qty": 10}}
    """
    result = log_append(agent_id, body.action, body.result, body.metadata)
    if not result.get("logged"):
        raise HTTPException(status_code=429, detail=result)
    return result


@app.get("/logs/{agent_id}")
def get_agent_logs(
    agent_id: str,
    limit: int = Query(default=100, ge=1, le=1000),
    action: str = Query(default=None, description="Filter by action type"),
):
    """
    Retrieve audit log entries for an agent. Free.

    Returns most recent entries first.
    Filter by action type with ?action=TRADE
    """
    return log_get(agent_id, limit=limit, action_filter=action)


@app.get("/logs/{agent_id}/stats")
def get_agent_log_stats(agent_id: str):
    """Per-agent audit log statistics. Free."""
    return log_agent_stats(agent_id)
