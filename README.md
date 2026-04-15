# Signal API

**Momentum trading signals for AI agents. Pay per call. No signup.**

Your AI trading agent needs market signals. This API serves them — RSI, ADX, MACD, volume confirmation, composite scoring — and charges per call in USDC via the [x402 protocol](https://x402.org). No API keys. No subscriptions. No humans in the loop.

## Endpoints

| Endpoint | Price | Returns |
|---|---|---|
| `GET /signal/{ticker}` | $0.005 | BUY/SELL/HOLD + confidence score + RSI, ADX, MACD, volume ratio, ATR |
| `GET /scan/momentum` | $0.01 | Top momentum setups from 35+ US equities |
| `GET /risk?tickers=AAPL,NVDA` | $0.01 | Portfolio risk: volatility, drawdown, correlation, Sharpe |
| `GET /health` | Free | Status check |
| `GET /pricing` | Free | Machine-readable price list |

## How It Works

```
1. Agent calls GET /signal/NVDA
2. Gets HTTP 402 + payment instructions
3. Agent wallet signs USDC transfer on Base L2
4. Agent retries with payment header
5. Gets signal data. Done.
```

All payment logic is handled by the x402 protocol. If your agent has an x402-compatible wallet, it just works.

## Example Response

```json
{
  "ticker": "NVDA",
  "signal": "BUY",
  "confidence": 0.65,
  "rsi": 42.18,
  "adx": 28.34,
  "macd": 1.2847,
  "macd_signal": 0.9213,
  "volume_ratio": 1.73,
  "atr_pct": 2.41,
  "price": 892.50,
  "change_pct": 2.14,
  "timestamp": "2026-04-15T14:30:00-04:00"
}
```

## For Agent Developers

Install the x402 client SDK:

```bash
pip install x402
```

```python
import httpx
from x402.clients.httpx import x402_payment_headers

response = httpx.get(
    "https://signal-api.fly.dev/signal/AAPL",
    headers=x402_payment_headers(wallet, network="eip155:8453")
)
print(response.json())
```

Works with any x402-compatible client (Python, TypeScript, Go, Rust, Java).

## Scoring Model

Composite momentum score from 4 weighted components:

- **RSI (14)** — oversold/overbought detection
- **ADX (14)** — trend strength filter (>25 = strong trend)
- **MACD (12/26/9)** — crossover + direction
- **Volume ratio** — current vs 20-day average (confirmation)

Score maps to BUY (>=30), SELL (<=-30), or HOLD. Confidence = |score| / 100.

## Self-Host

```bash
cp .env.example .env
# Set EVM_ADDRESS to your Base L2 wallet
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

## License

MIT
