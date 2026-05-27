"""Quant research engine — backtesting and alpha fusion."""

from quant_core.research.alpha_fusion import composite_alpha, fuse_multi_asset
from quant_core.research.backtest import (
    BacktestResult,
    purged_walk_forward_splits,
    walk_forward_ml_backtest,
)

__all__ = [
    "BacktestResult",
    "composite_alpha",
    "fuse_multi_asset",
    "purged_walk_forward_splits",
    "walk_forward_ml_backtest",
]
