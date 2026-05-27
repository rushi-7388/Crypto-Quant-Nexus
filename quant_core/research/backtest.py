"""Walk-forward and purged backtesting for time-series ML signals."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, Iterator

import numpy as np
import pandas as pd

from quant_core.metrics import performance_summary

logger = logging.getLogger(__name__)


@dataclass
class BacktestResult:
    equity_curve: pd.Series
    strategy_returns: pd.Series
    benchmark_returns: pd.Series
    metrics: dict[str, float]
    folds: list[dict[str, Any]]
    symbol: str


def purged_walk_forward_splits(
    n_samples: int,
    train_size: int,
    test_size: int,
    purge_gap: int = 5,
) -> Iterator[tuple[np.ndarray, np.ndarray]]:
    """
  Expanding-window walk-forward with purge gap (Lopez de Prado style).
  Prevents label leakage between train and test segments.
    """
    start = train_size
    while start + test_size + purge_gap <= n_samples:
        train_idx = np.arange(0, start)
        test_idx = np.arange(start + purge_gap, start + purge_gap + test_size)
        yield train_idx, test_idx
        start += test_size


def walk_forward_ml_backtest(
    df: pd.DataFrame,
    feature_builder: Callable[[pd.DataFrame], pd.DataFrame],
    trainer: Callable[[pd.DataFrame], Any],
    predictor: Callable[[Any, pd.DataFrame], pd.Series],
    horizon_bars: int = 3,
    train_size: int = 280,
    test_size: int = 40,
    purge_gap: int = 5,
    symbol: str = "BTC/USDT",
) -> BacktestResult:
    """
    Walk-forward backtest: retrain per fold, apply positions on out-of-sample bars.
    Position: +1 long if prob_up > 0.55, -1 short if < 0.45, else flat.
    """
    featured = feature_builder(df.copy())
    featured["fwd_ret"] = featured["close"].shift(-horizon_bars) / featured["close"] - 1
    featured = featured.dropna(subset=["close", "fwd_ret"])

    fold_results: list[dict[str, Any]] = []
    oos_returns: list[float] = []
    oos_index: list[Any] = []

    n = len(featured)
    for fold_id, (train_idx, test_idx) in enumerate(
        purged_walk_forward_splits(n, train_size, test_size, purge_gap)
    ):
        train_df = featured.iloc[train_idx]
        test_df = featured.iloc[test_idx]
        if len(train_df) < 50 or len(test_df) < 5:
            continue

        try:
            artifact = trainer(train_df)
            proba = predictor(artifact, test_df)
        except Exception as exc:
            logger.warning("backtest_fold_failed fold=%s error=%s", fold_id, exc)
            continue

        aligned = test_df.loc[proba.index]
        position = pd.Series(0.0, index=proba.index)
        position.loc[proba > 0.55] = 1.0
        position.loc[proba < 0.45] = -1.0
        strat_ret = position * aligned["fwd_ret"]
        oos_returns.extend(strat_ret.tolist())
        oos_index.extend(test_df["timestamp"].tolist() if "timestamp" in test_df else test_df.index.tolist())

        fold_acc = float(((proba > 0.5) == (aligned["fwd_ret"] > 0)).mean())
        fold_results.append(
            {
                "fold": fold_id,
                "train_bars": len(train_df),
                "test_bars": len(test_df),
                "accuracy": fold_acc,
                "mean_return": float(strat_ret.mean()),
            }
        )

    if not oos_returns:
        empty = pd.Series(dtype=float)
        return BacktestResult(
            equity_curve=empty,
            strategy_returns=empty,
            benchmark_returns=featured["fwd_ret"],
            metrics=performance_summary(empty),
            folds=fold_results,
            symbol=symbol,
        )

    strat_series = pd.Series(oos_returns, index=range(len(oos_returns)))
    equity = (1 + strat_series).cumprod()
    bench = featured["fwd_ret"].iloc[-len(oos_returns) :].reset_index(drop=True)

    return BacktestResult(
        equity_curve=equity,
        strategy_returns=strat_series,
        benchmark_returns=bench,
        metrics=performance_summary(strat_series),
        folds=fold_results,
        symbol=symbol,
    )
