"""Train and register Regime Nexus K-Means model."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from quant_core.data import resolve_price_feed
from quant_core.logging_config import configure_logging
from quant_core.ml.regime_model import save_regime_artifact, train_regime_model
from quant_core.ml.tracking import log_sklearn_model, mlflow_run

configure_logging(service_name="mlops-regime-nexus")


def main() -> None:
    parser = argparse.ArgumentParser(description="Train Regime Nexus K-Means model")
    parser.add_argument("--symbol", default="BTC/USDT")
    parser.add_argument("--regimes", type=int, default=4)
    parser.add_argument("--window", type=int, default=600)
    parser.add_argument("--output", default="artifacts/models/regime_nexus")
    parser.add_argument("--no-live", action="store_true")
    args = parser.parse_args()

    df, label = resolve_price_feed(args.symbol, use_live=not args.no_live)
    df = df.tail(args.window)

    with mlflow_run("regime-nexus", run_name=f"{args.symbol}-k{args.regimes}") as run:
        artifact, _ = train_regime_model(df, n_regimes=args.regimes)
        out = save_regime_artifact(artifact, args.output)
        if run is not None:
            import mlflow

            mlflow.log_param("symbol", args.symbol)
            mlflow.log_param("n_regimes", args.regimes)
            mlflow.log_param("feed", label)
            mlflow.log_metric("inertia", float(artifact.kmeans.inertia_))
            log_sklearn_model(artifact.kmeans, "regime_kmeans", registered_name="regime-nexus-kmeans")

    print(f"Regime Nexus trained k={args.regimes} saved={out}")


if __name__ == "__main__":
    main()
