"""
Agent Infrastructure API — trading signals, memory, and identity for AI agents.

Agents pay per call in USDC on Base L2. No signup, no API keys, no subscriptions.
"""

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

    # Memory endpoints — pay per read/write
    paid_routes["GET /memory/*/*"] = RouteConfig(
        accepts=[PaymentOption(scheme="exact", pay_to=settings.evm_address, price="$0.001", network=settings.network)],
        mime_type="application/json", description="Read a value from agent memory.",
    )
    paid_routes["PUT /memory/*/*"] = RouteConfig(
        accepts=[PaymentOption(scheme="exact", pay_to=settings.evm_address, price="$0.002", network=settings.network)],
        mime_type="application/json", description="Write a value to agent memory.",
    )
    paid_routes["DELETE /memory/*/*"] = RouteConfig(
        accepts=[PaymentOption(scheme="exact", pay_to=settings.evm_address, price="$0.001", network=settings.network)],
        mime_type="application/json", description="Delete a value from agent memory.",
    )
    paid_routes["GET /memory/*"] = RouteConfig(
        accepts=[PaymentOption(scheme="exact", pay_to=settings.evm_address, price="$0.002", network=settings.network)],
        mime_type="application/json", description="List keys in a memory namespace.",
    )

    # Identity endpoints — lookup costs, registration is free
    paid_routes["GET /identity/lookup/*"] = RouteConfig(
        accepts=[PaymentOption(scheme="exact", pay_to=settings.evm_address, price="$0.001", network=settings.network)],
        mime_type="application/json", description="Look up an agent's identity and reputation.",
    )
    paid_routes["GET /identity/search"] = RouteConfig(
        accepts=[PaymentOption(scheme="exact", pay_to=settings.evm_address, price="$0.002", network=settings.network)],
        mime_type="application/json", description="Search agents by capability.",
    )
    paid_routes["POST /identity/review"] = RouteConfig(
        accepts=[PaymentOption(scheme="exact", pay_to=settings.evm_address, price="$0.003", network=settings.network)],
        mime_type="application/json", description="Leave a reputation review for an agent.",
    )

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
                "GET /memory/{ns}/{key}": "$0.001 - Read value",
                "GET /memory/{ns}": "$0.002 - List keys",
            },
            "identity": {
                "POST /identity/register": "FREE - Register agent",
                "GET /identity/lookup/{id}": "$0.001 - Lookup agent",
                "GET /identity/search": "$0.002 - Search agents",
                "POST /identity/review": "$0.003 - Leave review",
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
        "description_for_model": "API for retrieving momentum-based trading signals for US equities. Returns BUY/SELL/HOLD with confidence scores, RSI, ADX, MACD, volume ratio, ATR, and composite scoring. Also provides momentum scanning across 35+ tickers and portfolio risk analysis. Payment via x402 protocol (USDC on Base L2). Endpoints: GET /signal/{ticker} for single stock signal, GET /scan/momentum for top setups, GET /risk?tickers=X,Y,Z for portfolio risk.",
        "auth": {
            "type": "none",
            "instructions": "Payment handled via x402 protocol. No API key needed. Agent wallet pays per call in USDC on Base L2."
        },
        "api": {
            "type": "openapi",
            "url": "https://signal-api-lively-sky-8407.fly.dev/openapi.json",
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
        "url": "https://signal-api-lively-sky-8407.fly.dev",
        "version": "1.0.0",
        "capabilities": ["trading-signals", "momentum-analysis", "portfolio-risk", "market-scanning"],
        "payment": {
            "protocol": "x402",
            "currency": "USDC",
            "network": "Base L2",
            "min_price": "$0.005",
        },
        "api_spec": "https://signal-api-lively-sky-8407.fly.dev/openapi.json",
        "authentication": "none",
        "contact": "p.mestre@live.com.pt",
    })


# ---------------------------------------------------------------------------
# Free endpoints
# ---------------------------------------------------------------------------
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
            "GET /memory/{ns}/{key}": "$0.001",
            "PUT /memory/{ns}/{key}": "$0.002",
            "DELETE /memory/{ns}/{key}": "$0.001",
            "GET /memory/{ns}": "$0.002",
        },
        "identity": {
            "POST /identity/register": "FREE",
            "GET /identity/lookup/{id}": "$0.001",
            "GET /identity/search": "$0.002",
            "POST /identity/review": "$0.003",
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


@app.get("/memory/stats")
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
class RegisterBody(BaseModel):
    name: str
    description: str = ""
    wallet_address: str = ""
    capabilities: list[str] = []


class ReviewBody(BaseModel):
    reviewer_id: str
    target_id: str
    score: float
    comment: str = ""


@app.post("/identity/register")
def post_register(body: RegisterBody):
    """Register a new agent identity. Free."""
    if not body.name or len(body.name) > 100:
        raise HTTPException(status_code=400, detail="Name required, max 100 chars.")
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


@app.get("/identity/stats")
def get_identity_stats():
    """Identity service stats. Free."""
    return identity_stats()
