"""
Signal API — AI-agent-facing trading signals with x402 micropayments.

Agents pay per call in USDC on Base L2. No signup, no API keys, no subscriptions.
"""

import re
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from x402.http import FacilitatorConfig, HTTPFacilitatorClient, PaymentOption
from x402.http.middleware.fastapi import PaymentMiddlewareASGI
from x402.http.types import RouteConfig
from x402.mechanisms.evm.exact import ExactEvmServerScheme
from x402.server import x402ResourceServer

from fastapi.responses import JSONResponse

from config import settings
from signals import compute_risk, compute_signal, scan_momentum

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Signal API",
    description="Momentum trading signals for AI agents. Pay per call via x402 (USDC on Base).",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
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
        "name": "Signal API",
        "description": "Momentum trading signals for AI agents. Pay per call in USDC via x402.",
        "version": "1.0.0",
        "protocol": "x402",
        "docs": "/docs",
        "openapi": "/openapi.json",
        "pricing": "/pricing",
        "health": "/health",
        "plugin_manifest": "/.well-known/ai-plugin.json",
        "github": "https://github.com/pmestre-Forge/signal-api",
        "endpoints": {
            "GET /signal/{ticker}": {"price": "$0.005", "description": "Momentum signal for a single stock"},
            "GET /scan/momentum": {"price": "$0.01", "description": "Top momentum BUY setups from 35+ stocks"},
            "GET /risk?tickers=X,Y,Z": {"price": "$0.01", "description": "Portfolio risk analysis"},
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
        "endpoints": {
            "/signal/{ticker}": f"${settings.price_signal}",
            "/scan/momentum": f"${settings.price_scan}",
            "/risk?tickers=X,Y,Z": f"${settings.price_risk}",
        },
        "protocol": "x402",
        "docs": "https://x402.org",
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
