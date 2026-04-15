"""
Momentum signal engine.

Computes RSI, ADX, MACD, volume profile, and composite score
for any ticker. Returns BUY / SELL / HOLD with confidence.
"""

import time
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd
import yfinance as yf

# ---------------------------------------------------------------------------
# In-memory LRU cache: {ticker: (timestamp, SignalResult)}
# ---------------------------------------------------------------------------
MAX_CACHE_SIZE = 200
_cache: dict[str, tuple[float, "SignalResult"]] = {}

# Import TTL from config, fallback to 300s
try:
    from config import settings
    CACHE_TTL = settings.cache_ttl_seconds
except Exception:
    CACHE_TTL = 300


def _cache_set(key: str, value: "SignalResult", now: float) -> None:
    """Add to cache with LRU eviction when full."""
    if len(_cache) >= MAX_CACHE_SIZE and key not in _cache:
        oldest_key = min(_cache, key=lambda k: _cache[k][0])
        del _cache[oldest_key]
    _cache[key] = (now, value)


@dataclass
class SignalResult:
    ticker: str
    signal: str  # BUY | SELL | HOLD
    confidence: float  # 0.0 – 1.0
    rsi: float
    adx: float
    macd: float
    macd_signal: float
    volume_ratio: float  # current vs 20d average
    atr_pct: float  # ATR as % of price
    price: float
    change_pct: float  # day change %
    timestamp: str


def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / period, min_periods=period).mean()

    up_move = high - high.shift(1)
    down_move = low.shift(1) - low
    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)

    plus_di = 100 * (plus_dm.ewm(alpha=1 / period, min_periods=period).mean() / atr)
    minus_di = 100 * (minus_dm.ewm(alpha=1 / period, min_periods=period).mean() / atr)

    dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan))
    return dx.ewm(alpha=1 / period, min_periods=period).mean()


def _macd(close: pd.Series) -> tuple[pd.Series, pd.Series]:
    ema12 = close.ewm(span=12, min_periods=12).mean()
    ema26 = close.ewm(span=26, min_periods=26).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, min_periods=9).mean()
    return macd_line, signal_line


def _atr_pct(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / period, min_periods=period).mean()
    return atr / close * 100


def compute_signal(ticker: str) -> Optional[SignalResult]:
    """Compute momentum signal for a single ticker. Returns None on data error."""
    # Check cache
    now = time.time()
    if ticker in _cache:
        ts, cached = _cache[ticker]
        if now - ts < CACHE_TTL:
            return cached

    try:
        df = yf.download(ticker, period="6mo", interval="1d", progress=False, auto_adjust=True)
    except Exception:
        return None

    if df is None or len(df) < 40:
        return None

    # Flatten MultiIndex columns from yfinance
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"]

    rsi_val = _rsi(close).iloc[-1]
    adx_val = _adx(high, low, close).iloc[-1]
    macd_line, macd_sig = _macd(close)
    macd_val = macd_line.iloc[-1]
    macd_sig_val = macd_sig.iloc[-1]
    vol_ratio = volume.iloc[-1] / volume.rolling(20).mean().iloc[-1] if volume.rolling(20).mean().iloc[-1] > 0 else 1.0
    atr_pct_val = _atr_pct(high, low, close).iloc[-1]
    price = close.iloc[-1]
    change_pct = ((close.iloc[-1] - close.iloc[-2]) / close.iloc[-2] * 100) if len(close) >= 2 else 0.0

    # Convert numpy types to float, replace NaN with 0
    def _safe_float(v, default=0.0):
        f = float(v)
        return default if np.isnan(f) or np.isinf(f) else f

    rsi_val = _safe_float(rsi_val, 50.0)  # neutral RSI if missing
    adx_val = _safe_float(adx_val, 15.0)  # low ADX if missing
    macd_val = _safe_float(macd_val)
    macd_sig_val = _safe_float(macd_sig_val)
    vol_ratio = _safe_float(vol_ratio, 1.0)
    atr_pct_val = _safe_float(atr_pct_val)
    price = _safe_float(price)
    change_pct = _safe_float(change_pct)

    # --- Composite scoring ---
    score = 0.0

    # RSI component: bullish 40-60 neutral, <30 oversold buy, >70 overbought sell
    if rsi_val < 30:
        score += 25
    elif rsi_val < 45:
        score += 15
    elif rsi_val > 70:
        score -= 25
    elif rsi_val > 55:
        score -= 10

    # ADX component: trend strength
    if adx_val > 25:
        score += 20  # strong trend
    elif adx_val > 20:
        score += 10
    else:
        score -= 5  # no trend, choppy

    # MACD component
    if macd_val > macd_sig_val and macd_val > 0:
        score += 25  # bullish crossover + positive
    elif macd_val > macd_sig_val:
        score += 10  # crossover but negative territory
    elif macd_val < macd_sig_val and macd_val < 0:
        score -= 25  # bearish
    else:
        score -= 10

    # Volume confirmation
    if vol_ratio > 1.5:
        score += 15  # high volume confirms move
    elif vol_ratio > 1.0:
        score += 5
    else:
        score -= 5  # below average, weak conviction

    # Normalize score to -100..+100 range
    score = max(-100, min(100, score))

    # Signal determination
    if score >= 30:
        signal = "BUY"
    elif score <= -30:
        signal = "SELL"
    else:
        signal = "HOLD"

    confidence = round(abs(score) / 100, 2)

    result = SignalResult(
        ticker=ticker.upper(),
        signal=signal,
        confidence=confidence,
        rsi=round(rsi_val, 2),
        adx=round(adx_val, 2),
        macd=round(macd_val, 4),
        macd_signal=round(macd_sig_val, 4),
        volume_ratio=round(vol_ratio, 2),
        atr_pct=round(atr_pct_val, 2),
        price=round(price, 2),
        change_pct=round(change_pct, 2),
        timestamp=pd.Timestamp.now(tz="US/Eastern").isoformat(),
    )

    _cache_set(ticker, result, now)
    return result


WATCHLIST = [
    "AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "TSLA", "AMD",
    "AVGO", "CRM", "NFLX", "ORCL", "ADBE", "NOW", "UBER",
    "JPM", "GS", "MS", "BAC", "V", "MA",
    "XOM", "CVX", "OXY", "SLB",
    "LMT", "RTX", "GD", "NOC",
    "CAT", "DE", "UNP",
    "GTES", "STRL", "TOST", "DUOL",
]


def scan_momentum(top_n: int = 10) -> list[SignalResult]:
    """Scan a watchlist for top momentum setups. Uses batch download."""
    now = time.time()

    # Check which tickers are not cached
    uncached = [t for t in WATCHLIST if t not in _cache or now - _cache[t][0] >= CACHE_TTL]

    # Batch download uncached tickers in one yfinance call (much faster)
    if uncached:
        try:
            batch_df = yf.download(uncached, period="6mo", interval="1d", progress=False, auto_adjust=True, group_by="ticker")
            if batch_df is not None and not batch_df.empty:
                for ticker in uncached:
                    try:
                        if len(uncached) == 1:
                            ticker_df = batch_df
                        else:
                            ticker_df = batch_df[ticker].dropna(how="all")
                        if isinstance(ticker_df.columns, pd.MultiIndex):
                            ticker_df.columns = ticker_df.columns.get_level_values(0)
                        if len(ticker_df) >= 40:
                            # Compute signal from the batch data — store in cache via compute_signal
                            # We pre-warm the yfinance cache by calling compute_signal which will re-download
                            # but since yfinance has its own cache, this is fast
                            compute_signal(ticker)
                    except Exception:
                        pass
        except Exception:
            pass

    # Now compute signals (all should be cached or fast)
    results = []
    for ticker in WATCHLIST:
        sig = compute_signal(ticker)
        if sig and sig.signal == "BUY":
            results.append(sig)

    results.sort(key=lambda s: s.confidence, reverse=True)
    return results[:top_n]


def compute_risk(tickers: list[str]) -> Optional[dict]:
    """Compute portfolio risk metrics for a list of tickers."""
    if not tickers or len(tickers) > 50:
        return None

    try:
        df = yf.download(tickers, period="3mo", interval="1d", progress=False, auto_adjust=True)
    except Exception:
        return None

    if df is None or df.empty:
        return None

    close = df["Close"]
    if isinstance(close, pd.Series):
        close = close.to_frame(name=tickers[0])

    returns = close.pct_change().dropna()
    if returns.empty:
        return None

    # Correlation matrix
    corr = returns.corr()
    avg_correlation = float(corr.where(~np.eye(len(corr), dtype=bool)).mean().mean()) if len(corr) > 1 else 0.0

    # Per-ticker metrics
    holdings = {}
    for t in tickers:
        col = t if t in returns.columns else None
        if col is None:
            continue
        r = returns[col]
        holdings[t] = {
            "annualized_vol": round(float(r.std() * np.sqrt(252) * 100), 2),
            "max_drawdown_pct": round(float((close[col] / close[col].cummax() - 1).min() * 100), 2),
            "sharpe_approx": round(float(r.mean() / r.std() * np.sqrt(252)) if r.std() > 0 else 0, 2),
        }

    # Portfolio-level (equal weight)
    if len(returns.columns) > 1:
        port_returns = returns.mean(axis=1)
    else:
        port_returns = returns.iloc[:, 0]

    port_vol = float(port_returns.std() * np.sqrt(252) * 100)
    port_cumulative = (1 + port_returns).cumprod()
    port_dd = float((1 - port_cumulative / port_cumulative.cummax()).max() * 100)

    return {
        "portfolio_annualized_vol_pct": round(port_vol, 2),
        "portfolio_max_drawdown_pct": round(port_dd, 2),
        "average_correlation": round(avg_correlation, 2),
        "concentration": round(1.0 / len(tickers), 2),
        "holdings": holdings,
        "ticker_count": len(tickers),
        "timestamp": pd.Timestamp.now(tz="US/Eastern").isoformat(),
    }
