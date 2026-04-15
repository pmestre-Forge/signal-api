"""
Signal API — AI-agent-facing trading signals with x402 micropayments.

Agents pay per call in USDC on Base L2. No signup, no API keys, no subscriptions.
"""

import re

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from x402.http import FacilitatorConfig, HTTPFacilitatorClient, PaymentOption
from x402.http.middleware.fastapi import PaymentMiddlewareASGI
from x402.http.types import RouteConfig
from x402.mechanisms.evm.exact import ExactEvmServerScheme
from x402.server import x402ResourceServer

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
