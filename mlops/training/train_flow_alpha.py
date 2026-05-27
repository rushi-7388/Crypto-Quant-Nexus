"""Train and register Flow Alpha model — run locally or in CI."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from quant_core.data import resolve_price_feed
from quant_core.logging_config import configure_logging
from quant_core.ml.flow_model import horizon_bars_from_label, save_flow_artifact, train_flow_model
from quant_core.ml.tracking import log_sklearn_model, mlflow_run

configure_logging(service_name="mlops-flow-alpha")


def main() -> None:
    parser = argparse.ArgumentParser(description="Train Flow Alpha gradient boosting model")
    parser.add_argument("--symbol", default="BTC/USDT")
    parser.add_argument("--horizon", default="3 bars")
    parser.add_argument("--window", type=int, default=500)
    parser.add_argument("--output", default="artifacts/models/flow_alpha")
    parser.add_argument("--no-live", action="store_true")
    args = parser.parse_args()

    df, label = resolve_price_feed(args.symbol, use_live=not args.no_live)
    df = df.tail(args.window)
    horizon = horizon_bars_from_label(args.horizon)

    with mlflow_run("flow-alpha", run_name=f"{args.symbol}-{horizon}bar") as run:
        artifact = train_flow_model(df, horizon_bars=horizon)
        out = save_flow_artifact(artifact, args.output)
        if run is not None:
            import mlflow

            mlflow.log_param("symbol", args.symbol)
            mlflow.log_param("horizon_bars", horizon)
            mlflow.log_param("feed", label)
            mlflow.log_metric("accuracy", artifact.accuracy)
            log_sklearn_model(artifact.model, "flow_gbc", registered_name="flow-alpha-gbc")

    print(f"Flow Alpha trained accuracy={artifact.accuracy:.4f} saved={out}")


if __name__ == "__main__":
    main()
