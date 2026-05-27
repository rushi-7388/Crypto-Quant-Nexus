"""Walk-forward backtest for Flow Alpha pipeline."""

from __future__ import annotations

import pandas as pd

from quant_core.ml.flow_model import build_flow_features, train_flow_model
from quant_core.research.backtest import BacktestResult, walk_forward_ml_backtest


def _predict_proba_series(artifact, df: pd.DataFrame) -> pd.Series:
    featured = build_flow_features(df)
    featured = featured.dropna(subset=list(artifact.features))
    if featured.empty:
        return pd.Series(dtype=float)
    X = featured[list(artifact.features)]
    proba = artifact.model.predict_proba(artifact.scaler.transform(X))[:, 1]
    return pd.Series(proba, index=featured.index)


def run_flow_alpha_backtest(
    df: pd.DataFrame,
    horizon_bars: int = 3,
    symbol: str = "BTC/USDT",
) -> BacktestResult:
    return walk_forward_ml_backtest(
        df=df,
        feature_builder=build_flow_features,
        trainer=lambda train_df: train_flow_model(train_df, horizon_bars=horizon_bars),
        predictor=_predict_proba_series,
        horizon_bars=horizon_bars,
        symbol=symbol,
    )
