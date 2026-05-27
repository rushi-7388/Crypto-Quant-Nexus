"""Multi-asset universe and reproducible parquet research cache."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from quant_core.data import resolve_price_feed

logger = logging.getLogger(__name__)

DEFAULT_CACHE_DIR = Path("artifacts/data/cache")

ASSET_UNIVERSE: dict[str, dict[str, str]] = {
    "BTC/USDT": {"tier": "L1", "sector": "store-of-value", "yf": "BTC-USD"},
    "ETH/USDT": {"tier": "L1", "sector": "smart-contract", "yf": "ETH-USD"},
    "SOL/USDT": {"tier": "L1", "sector": "smart-contract", "yf": "SOL-USD"},
    "BNB/USDT": {"tier": "L1", "sector": "exchange", "yf": "BNB-USD"},
    "XRP/USDT": {"tier": "L1", "sector": "payments", "yf": "XRP-USD"},
    "AVAX/USDT": {"tier": "L1", "sector": "smart-contract", "yf": "AVAX-USD"},
}


def list_universe(tier: str | None = None) -> list[str]:
    if tier is None:
        return list(ASSET_UNIVERSE.keys())
    return [s for s, m in ASSET_UNIVERSE.items() if m.get("tier") == tier]


def cache_ohlcv(
    symbol: str,
    use_live: bool = True,
    cache_dir: Path | str = DEFAULT_CACHE_DIR,
) -> Path:
    df, label = resolve_price_feed(symbol, use_live=use_live)
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    safe = symbol.replace("/", "_")
    path = cache_dir / f"{safe}.parquet"
    out = df.copy()
    out["symbol"] = symbol
    out["feed_label"] = label
    out.to_parquet(path, index=False)
    logger.info("ohlcv_cached symbol=%s path=%s rows=%s", symbol, path, len(out))
    return path


def load_cached_ohlcv(
    symbol: str,
    cache_dir: Path | str = DEFAULT_CACHE_DIR,
) -> pd.DataFrame | None:
    path = Path(cache_dir) / f"{symbol.replace('/', '_')}.parquet"
    if not path.exists():
        return None
    return pd.read_parquet(path)
