"""K-Means regime detection with persisted cluster models."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

import joblib
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

REGIME_FEATURE_COLS = ("ret", "vol_20", "mom_10", "range_pct")
DEFAULT_REGIME_NAMES = {
    0: "Accumulation",
    1: "Bull Trend",
    2: "Bear Trend",
    3: "High Vol / Panic",
}
DEFAULT_ARTIFACT_DIR = Path("artifacts/models/regime_nexus")


@dataclass
class RegimeModelArtifact:
    kmeans: KMeans
    scaler: StandardScaler
    feature_columns: tuple[str, ...]
    regime_names: dict[int, str]
    n_regimes: int
    version: str = "1"


def build_regime_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["ret"] = out["close"].pct_change()
    out["vol_20"] = out["ret"].rolling(20).std()
    out["mom_10"] = out["close"].pct_change(10)
    out["range_pct"] = (out["high"] - out["low"]) / out["close"]
    return out


def _name_for_cluster(cluster_id: int, n_regimes: int) -> str:
    if cluster_id in DEFAULT_REGIME_NAMES and n_regimes == 4:
        return DEFAULT_REGIME_NAMES[cluster_id]
    return f"Regime {cluster_id}"


def train_regime_model(
    df: pd.DataFrame,
    n_regimes: int = 4,
    random_state: int = 42,
) -> tuple[RegimeModelArtifact, pd.DataFrame]:
    """Fit K-Means on volatility/momentum features; return labeled frame."""
    featured = build_regime_features(df)
    feat = featured[list(REGIME_FEATURE_COLS)].dropna()
    idx = feat.index

    scaler = StandardScaler()
    scaled = scaler.fit_transform(feat)
    kmeans = KMeans(n_clusters=n_regimes, random_state=random_state, n_init=10)
    labels = kmeans.fit_predict(scaled)

    featured.loc[idx, "regime"] = labels
    featured["regime_name"] = featured["regime"].map(
        lambda x: _name_for_cluster(int(x), n_regimes) if pd.notna(x) else ""
    )

    names = {i: _name_for_cluster(i, n_regimes) for i in range(n_regimes)}
    artifact = RegimeModelArtifact(
        kmeans=kmeans,
        scaler=scaler,
        feature_columns=REGIME_FEATURE_COLS,
        regime_names=names,
        n_regimes=n_regimes,
    )
    logger.info("regime_model_trained n_regimes=%s samples=%s", n_regimes, len(feat))
    return artifact, featured


def detect_regimes(artifact: RegimeModelArtifact, df: pd.DataFrame) -> pd.DataFrame:
    """Apply a trained regime model to new OHLCV data."""
    featured = build_regime_features(df)
    feat = featured[list(artifact.feature_columns)].dropna()
    idx = feat.index
    labels = artifact.kmeans.predict(artifact.scaler.transform(feat))
    featured.loc[idx, "regime"] = labels
    featured["regime_name"] = featured["regime"].map(
        lambda x: artifact.regime_names.get(int(x), f"Regime {int(x)}") if pd.notna(x) else ""
    )
    return featured


def transition_matrix(df: pd.DataFrame) -> pd.DataFrame:
    return pd.crosstab(df["regime"].shift(1), df["regime"], dropna=True)


def save_regime_artifact(
    artifact: RegimeModelArtifact, directory: Path | str = DEFAULT_ARTIFACT_DIR
) -> Path:
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "kmeans": artifact.kmeans,
            "scaler": artifact.scaler,
            "feature_columns": artifact.feature_columns,
            "regime_names": artifact.regime_names,
            "n_regimes": artifact.n_regimes,
            "version": artifact.version,
        },
        directory / "model.joblib",
    )
    meta = {
        "feature_columns": list(artifact.feature_columns),
        "regime_names": artifact.regime_names,
        "n_regimes": artifact.n_regimes,
        "version": artifact.version,
    }
    (directory / "metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return directory


def load_regime_artifact(directory: Path | str = DEFAULT_ARTIFACT_DIR) -> RegimeModelArtifact | None:
    path = Path(directory) / "model.joblib"
    if not path.exists():
        return None
    payload = joblib.load(path)
    return RegimeModelArtifact(
        kmeans=payload["kmeans"],
        scaler=payload["scaler"],
        feature_columns=tuple(payload["feature_columns"]),
        regime_names={int(k): v for k, v in payload["regime_names"].items()},
        n_regimes=int(payload["n_regimes"]),
        version=str(payload.get("version", "1")),
    )
