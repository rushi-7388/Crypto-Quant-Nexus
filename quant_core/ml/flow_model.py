"""Order-flow gradient boosting pipeline with artifact persistence."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from quant_core.orderbook import order_flow_imbalance

logger = logging.getLogger(__name__)

FLOW_FEATURES = ("ofi", "ofi_ma", "pressure", "ret", "vol_ma")
DEFAULT_ARTIFACT_DIR = Path("artifacts/models/flow_alpha")


@dataclass
class FlowModelArtifact:
    model: GradientBoostingClassifier
    scaler: StandardScaler
    features: tuple[str, ...]
    horizon_bars: int
    accuracy: float
    version: str = "1"


def horizon_bars_from_label(label: str) -> int:
    mapping = {"1 bar": 1, "3 bars": 3, "5 bars": 5}
    return mapping.get(label, 3)


def build_flow_features(df: pd.DataFrame, seed: int = 99) -> pd.DataFrame:
    """Engineer OFI and microstructure features from OHLCV."""
    out = df.copy()
    rng = np.random.default_rng(seed)
    ofi_vals: list[float] = []
    prev_bid = out["volume"].iloc[0] * 0.4
    prev_ask = out["volume"].iloc[0] * 0.6
    for _, row in out.iterrows():
        bid_v = row["volume"] * rng.uniform(0.35, 0.55)
        ask_v = row["volume"] * rng.uniform(0.45, 0.65)
        ofi_vals.append(order_flow_imbalance(bid_v, ask_v, prev_bid, prev_ask))
        prev_bid, prev_ask = bid_v, ask_v

    out["ofi"] = ofi_vals
    out["ofi_ma"] = pd.Series(ofi_vals).rolling(5).mean()
    out["ret"] = out["close"].pct_change()
    out["vol_ma"] = out["volume"].rolling(10).mean()
    out["pressure"] = out["ofi_ma"] / (out["vol_ma"] + 1)
    return out.dropna(subset=["close", "volume"]).reset_index(drop=True)


def train_flow_model(
    df: pd.DataFrame,
    horizon_bars: int = 3,
    test_size: float = 0.25,
    random_state: int = 42,
    n_estimators: int = 80,
    max_depth: int = 3,
) -> FlowModelArtifact:
    """Fit gradient boosting on OFI features; target is forward price direction."""
    featured = build_flow_features(df)
    featured["target"] = (featured["close"].shift(-horizon_bars) > featured["close"]).astype(int)
    featured = featured.dropna()

    X = featured[list(FLOW_FEATURES)]
    y = featured["target"]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, shuffle=False
    )
    scaler = StandardScaler()
    model = GradientBoostingClassifier(
        n_estimators=n_estimators,
        max_depth=max_depth,
        random_state=random_state,
    )
    model.fit(scaler.fit_transform(X_train), y_train)
    preds = model.predict(scaler.transform(X_test))
    accuracy = float((preds == y_test).mean()) if len(y_test) else 0.0

    logger.info(
        "flow_model_trained horizon_bars=%s accuracy=%.4f samples=%s",
        horizon_bars,
        accuracy,
        len(featured),
    )
    return FlowModelArtifact(
        model=model,
        scaler=scaler,
        features=FLOW_FEATURES,
        horizon_bars=horizon_bars,
        accuracy=accuracy,
    )


def predict_flow_signal(artifact: FlowModelArtifact, row: pd.DataFrame) -> dict[str, Any]:
    """Return direction signal and confidence for the latest feature row."""
    X = row[list(artifact.features)].dropna().tail(1)
    if X.empty:
        return {
            "signal": "NEUTRAL",
            "probability_up": 0.5,
            "confidence": 0.5,
            "horizon_bars": artifact.horizon_bars,
        }
    proba = float(artifact.model.predict_proba(artifact.scaler.transform(X))[:, 1][0])
    if proba > 0.55:
        signal = "BULLISH"
    elif proba < 0.45:
        signal = "BEARISH"
    else:
        signal = "NEUTRAL"
    return {
        "signal": signal,
        "probability_up": proba,
        "confidence": max(proba, 1 - proba),
        "horizon_bars": artifact.horizon_bars,
    }


def save_flow_artifact(artifact: FlowModelArtifact, directory: Path | str = DEFAULT_ARTIFACT_DIR) -> Path:
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "model": artifact.model,
            "scaler": artifact.scaler,
            "features": artifact.features,
            "horizon_bars": artifact.horizon_bars,
            "accuracy": artifact.accuracy,
            "version": artifact.version,
        },
        directory / "model.joblib",
    )
    meta = {k: v for k, v in asdict(artifact).items() if k not in ("model", "scaler")}
    meta["features"] = list(meta["features"])
    (directory / "metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return directory


def load_flow_artifact(directory: Path | str = DEFAULT_ARTIFACT_DIR) -> FlowModelArtifact | None:
    path = Path(directory) / "model.joblib"
    if not path.exists():
        return None
    payload = joblib.load(path)
    return FlowModelArtifact(
        model=payload["model"],
        scaler=payload["scaler"],
        features=tuple(payload["features"]),
        horizon_bars=int(payload["horizon_bars"]),
        accuracy=float(payload["accuracy"]),
        version=str(payload.get("version", "1")),
    )
