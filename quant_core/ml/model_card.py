"""Model cards for ML governance and portfolio documentation."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from quant_core.brand import AUTHOR, BRAND, VERSION


def flow_alpha_model_card(artifact_meta: dict[str, Any]) -> dict[str, Any]:
    return {
        "model_id": "flow-alpha-gbc-v1",
        "product": BRAND,
        "platform_version": VERSION,
        "owner": AUTHOR,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model_type": "GradientBoostingClassifier",
        "task": "binary_classification",
        "target": "forward_price_direction",
        "features": artifact_meta.get("features", ["ofi", "ofi_ma", "pressure", "ret", "vol_ma"]),
        "horizon_bars": artifact_meta.get("horizon_bars", 3),
        "reported_accuracy": artifact_meta.get("accuracy"),
        "intended_use": "Microstructure research and short-horizon directional bias — not live execution.",
        "limitations": [
            "Synthetic bid/ask volume split when true L2 unavailable",
            "Non-stationary crypto regimes",
            "No transaction cost model in training",
        ],
        "ethics": "Research-only; not investment advice.",
    }


def regime_nexus_model_card(artifact_meta: dict[str, Any]) -> dict[str, Any]:
    return {
        "model_id": "regime-nexus-kmeans-v1",
        "product": BRAND,
        "platform_version": VERSION,
        "owner": AUTHOR,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model_type": "KMeans",
        "task": "unsupervised_regime_clustering",
        "features": list(artifact_meta.get("feature_columns", [])),
        "n_regimes": artifact_meta.get("n_regimes", 4),
        "intended_use": "Market state labeling and transition analytics.",
        "limitations": [
            "Cluster labels are heuristic mappings",
            "Sensitive to feature scaling and lookback windows",
        ],
        "ethics": "Research-only; not investment advice.",
    }
