"""Data quality contracts for OHLCV feeds."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from quant_core.data import OHLCV_COLUMNS


def ohlcv_quality_report(df: pd.DataFrame) -> dict[str, Any]:
    if df is None or df.empty:
        return {"passed": False, "score": 0.0, "issues": ["empty_dataset"]}

    issues: list[str] = []
    missing_cols = [c for c in OHLCV_COLUMNS if c not in df.columns]
    if missing_cols:
        issues.append(f"missing_columns:{','.join(missing_cols)}")

    work = df.copy()
    for col in ("open", "high", "low", "close", "volume"):
        if col in work.columns:
            null_pct = float(work[col].isna().mean())
            if null_pct > 0.05:
                issues.append(f"high_null_rate:{col}={null_pct:.2%}")

    if all(c in work.columns for c in ("high", "low", "close")):
        if (work["high"] < work["low"]).sum() > 0:
            issues.append("invalid_high_low")
        if (work["close"] > work["high"]).sum() + (work["close"] < work["low"]).sum() > 0:
            issues.append("close_outside_hl_range")

    if "timestamp" in work.columns:
        ts = pd.to_datetime(work["timestamp"], errors="coerce")
        if int(ts.duplicated().sum()) > 0:
            issues.append("duplicate_timestamps")

    if "close" in work.columns:
        ret = work["close"].pct_change().dropna()
        if len(ret) > 10:
            z = (ret - ret.mean()) / (ret.std() + 1e-12)
            if int((np.abs(z) > 6).sum()) > 0:
                issues.append("return_spikes")

    score = max(0.0, 1.0 - 0.15 * len(issues))
    return {
        "passed": len(issues) == 0,
        "score": round(score, 4),
        "rows": len(work),
        "issues": issues,
    }
