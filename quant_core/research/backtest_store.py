"""Persist walk-forward backtest snapshots for copilot indexing."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RESEARCH_DIR = Path("artifacts/research")
BACKTEST_LOG = RESEARCH_DIR / "backtests.jsonl"


def persist_backtest_snapshot(
    *,
    symbol: str,
    feed: str,
    metrics: dict[str, float],
    folds: list[dict[str, Any]],
    oos_points: int,
    source: str = "api",
) -> dict[str, Any]:
    RESEARCH_DIR.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "symbol": symbol,
        "feed": feed,
        "metrics": metrics,
        "folds": folds,
        "oos_points": oos_points,
        "source": source,
    }
    with BACKTEST_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")
    return record


def read_backtest_snapshots(limit: int = 200) -> list[dict[str, Any]]:
    if not BACKTEST_LOG.exists():
        return []
    rows = [
        json.loads(line)
        for line in BACKTEST_LOG.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return rows[-limit:]
