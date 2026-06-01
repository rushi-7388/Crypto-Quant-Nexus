"""Feature contracts and online/offline parity checks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from quant_core.research.alpha_fusion import composite_alpha

CONTRACTS_PATH = Path("mlops/contracts/features.yaml")


@dataclass
class FeatureContract:
    name: str
    dtype: str
    min_value: float | None = None
    max_value: float | None = None
    nullable: bool = True


def load_contracts(path: Path | str = CONTRACTS_PATH) -> list[FeatureContract]:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    out: list[FeatureContract] = []
    for row in raw.get("features", []):
        out.append(
            FeatureContract(
                name=row["name"],
                dtype=row.get("dtype", "float"),
                min_value=row.get("min"),
                max_value=row.get("max"),
                nullable=bool(row.get("nullable", True)),
            )
        )
    return out


def _build_offline_vector(alpha_payload: dict[str, Any]) -> dict[str, Any]:
    c = alpha_payload["components"]
    return {
        "flow_score": c["flow"]["score"],
        "regime_score": c["regime"]["score"],
        "momentum_score": c["momentum"]["score"],
        "funding_score": c["funding"]["score"],
        "composite_score": alpha_payload["composite_score"],
        "conviction": alpha_payload["conviction"],
    }


def online_features(symbol: str, use_live: bool = True) -> dict[str, Any]:
    payload = composite_alpha(symbol=symbol, use_live=use_live)
    return _build_offline_vector(payload)


def offline_features(symbol: str) -> dict[str, Any]:
    # Offline parity run always deterministic via synthetic fallback path.
    payload = composite_alpha(symbol=symbol, use_live=False)
    return _build_offline_vector(payload)


def validate_features(features: dict[str, Any], contracts: list[FeatureContract]) -> list[str]:
    errors: list[str] = []
    for c in contracts:
        value = features.get(c.name)
        if value is None:
            if not c.nullable:
                errors.append(f"{c.name}:missing")
            continue
        if c.dtype == "float":
            try:
                f = float(value)
            except Exception:
                errors.append(f"{c.name}:not_float")
                continue
            if c.min_value is not None and f < c.min_value:
                errors.append(f"{c.name}:below_min")
            if c.max_value is not None and f > c.max_value:
                errors.append(f"{c.name}:above_max")
    return errors


def parity_report(symbol: str, tolerance: float = 0.35) -> dict[str, Any]:
    contracts = load_contracts()
    online = online_features(symbol, use_live=True)
    offline = offline_features(symbol)
    schema_errors = validate_features(online, contracts) + validate_features(offline, contracts)
    drift: dict[str, float] = {}
    for key in online:
        if isinstance(online[key], (int, float)) and isinstance(offline[key], (int, float)):
            drift[key] = abs(float(online[key]) - float(offline[key]))
    max_drift = max(drift.values()) if drift else 0.0
    return {
        "symbol": symbol,
        "schema_errors": schema_errors,
        "max_drift": max_drift,
        "within_tolerance": max_drift <= tolerance,
        "online": online,
        "offline": offline,
        "drift": drift,
    }


def parity_dataframe(symbols: list[str]) -> pd.DataFrame:
    rows = []
    for symbol in symbols:
        report = parity_report(symbol)
        rows.append(
            {
                "symbol": symbol,
                "max_drift": report["max_drift"],
                "within_tolerance": report["within_tolerance"],
                "schema_errors": len(report["schema_errors"]),
            }
        )
    return pd.DataFrame(rows)
