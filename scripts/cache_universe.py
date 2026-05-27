"""Cache full asset universe to parquet for reproducible research."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from quant_core.logging_config import configure_logging
from quant_core.platform.catalog import cache_ohlcv, list_universe

configure_logging(service_name="cache-universe")


def main() -> None:
    for symbol in list_universe():
        path = cache_ohlcv(symbol, use_live=False)
        print(f"cached {symbol} -> {path}")


if __name__ == "__main__":
    main()
