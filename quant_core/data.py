"""Live and synthetic market data with graceful exchange fallback."""

from __future__ import annotations

import logging
import time

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

OHLCV_COLUMNS = ("timestamp", "open", "high", "low", "close", "volume")


def _flatten_column_name(col: object) -> str:
    if isinstance(col, tuple):
        parts = [str(p).strip() for p in col if p is not None and str(p).strip()]
        return parts[0].lower().replace(" ", "_") if parts else ""
    return str(col).strip().lower().replace(" ", "_")


def normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure a consistent OHLCV schema regardless of data provider."""
    if df is None or df.empty:
        return synthetic_ohlcv()

    out = df.copy()
    if isinstance(out.columns, pd.MultiIndex):
        out.columns = [_flatten_column_name(c) for c in out.columns]
    else:
        out.columns = [_flatten_column_name(c) for c in out.columns]

    rename_map = {
        "datetime": "timestamp",
        "date": "timestamp",
        "adj_close": "close",
        "adj close": "close",
    }
    out = out.rename(columns={k: v for k, v in rename_map.items() if k in out.columns})

    # yfinance MultiIndex flatten can leave ticker suffixes, e.g. close_btc-usd
    for target in ("open", "high", "low", "close", "volume"):
        if target not in out.columns:
            match = next((c for c in out.columns if c == target or c.startswith(f"{target}_")), None)
            if match:
                out = out.rename(columns={match: target})

    if "timestamp" not in out.columns and out.index.name in (None, "date", "datetime", "timestamp"):
        out = out.reset_index()
        out.columns = [_flatten_column_name(c) for c in out.columns]
        out = out.rename(columns={"datetime": "timestamp", "date": "timestamp"})

    for col in ("open", "high", "low", "close", "volume"):
        if col not in out.columns:
            if col == "close" and "adj_close" in out.columns:
                out["close"] = out["adj_close"]
            elif col == "close" and len(out.select_dtypes(include="number").columns) > 0:
                out["close"] = out.select_dtypes(include="number").iloc[:, 0]
            else:
                out[col] = np.nan

    out = out[list(OHLCV_COLUMNS)].dropna(subset=["close"])
    out["timestamp"] = pd.to_datetime(out["timestamp"], utc=True, errors="coerce")
    for col in ("open", "high", "low", "close", "volume"):
        out[col] = pd.to_numeric(out[col], errors="coerce")
    return out.dropna(subset=["close"]).reset_index(drop=True)


def synthetic_ohlcv(n: int = 500, seed: int = 42, start_price: float = 95000.0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    returns = rng.normal(0, 0.0008, n)
    close = start_price * np.exp(np.cumsum(returns))
    high = close * (1 + rng.uniform(0, 0.0012, n))
    low = close * (1 - rng.uniform(0, 0.0012, n))
    volume = rng.integers(50_000, 2_000_000, n)
    ts = pd.date_range("2026-01-01", periods=n, freq="min", tz="UTC")
    return pd.DataFrame(
        {"timestamp": ts, "open": close, "high": high, "low": low, "close": close, "volume": volume}
    )


def fetch_yfinance_crypto(symbol: str = "BTC-USD", period: str = "5d", interval: str = "5m") -> pd.DataFrame | None:
    try:
        import yfinance as yf

        raw = yf.download(symbol, period=period, interval=interval, progress=False, auto_adjust=True)
        if raw is None or raw.empty:
            return None
        raw = raw.reset_index()
        return normalize_ohlcv(raw)
    except Exception:
        return None


def fetch_ccxt_ohlcv(
    symbol: str = "BTC/USDT",
    exchange_id: str = "binance",
    timeframe: str = "5m",
    limit: int = 300,
) -> pd.DataFrame | None:
    try:
        import ccxt

        exchange = getattr(ccxt, exchange_id)({"enableRateLimit": True})
        rows = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        if not rows:
            return None
        df = pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        return normalize_ohlcv(df)
    except Exception:
        return None


def resolve_price_feed(symbol: str = "BTC/USDT", use_live: bool = True) -> tuple[pd.DataFrame, str]:
    started = time.perf_counter()
    source = "synthetic"
    if use_live:
        live = fetch_ccxt_ohlcv(symbol)
        if live is not None and len(live) > 50:
            source = "ccxt"
            label = f"Live · {symbol} via CCXT"
            df = normalize_ohlcv(live)
            logger.info(
                'price_feed_resolved source=%s symbol="%s" rows=%s latency_ms=%.1f',
                source,
                symbol,
                len(df),
                (time.perf_counter() - started) * 1000,
            )
            return df, label
        yf_sym = symbol.replace("/", "-").replace("USDT", "USD")
        ylive = fetch_yfinance_crypto(yf_sym)
        if ylive is not None and len(ylive) > 50:
            source = "yfinance"
            label = f"Live · {yf_sym} via Yahoo Finance"
            df = normalize_ohlcv(ylive)
            logger.info(
                'price_feed_resolved source=%s symbol="%s" rows=%s latency_ms=%.1f',
                source,
                symbol,
                len(df),
                (time.perf_counter() - started) * 1000,
            )
            return df, label
    df = normalize_ohlcv(synthetic_ohlcv())
    logger.info(
        'price_feed_resolved source=%s symbol="%s" rows=%s latency_ms=%.1f',
        source,
        symbol,
        len(df),
        (time.perf_counter() - started) * 1000,
    )
    return df, "Synthetic research feed"


def fetch_funding_rates_demo() -> pd.DataFrame:
    """Cross-venue funding snapshot (live when CCXT works, else realistic synthetic)."""
    venues = [
        ("binance", "BTC/USDT:USDT"),
        ("bybit", "BTC/USDT:USDT"),
        ("okx", "BTC/USDT:USDT"),
    ]
    rows = []
    for ex_id, sym in venues:
        rate, src = _venue_funding(ex_id, sym)
        rows.append({"exchange": ex_id.title(), "symbol": "BTC-PERP", "funding_rate_pct": rate, "source": src})
    df = pd.DataFrame(rows)
    df["annualized_pct"] = df["funding_rate_pct"] * 3 * 365
    df["arb_score"] = df["funding_rate_pct"].max() - df["funding_rate_pct"].min()
    return df.sort_values("funding_rate_pct", ascending=False)


def _venue_funding(exchange_id: str, symbol: str) -> tuple[float, str]:
    try:
        import ccxt

        ex = getattr(ccxt, exchange_id)({"enableRateLimit": True})
        fr = ex.fetch_funding_rate(symbol)
        rate = float(fr.get("fundingRate", 0) or 0) * 100
        return rate, "live"
    except Exception:
        rng = np.random.default_rng(hash(exchange_id) % 2**32)
        return float(rng.uniform(-0.02, 0.05)), "synthetic"
