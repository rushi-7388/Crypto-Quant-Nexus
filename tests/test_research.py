"""Research engine — backtest, alpha fusion."""

import numpy as np

from quant_core.data import synthetic_ohlcv
from quant_core.research.alpha_fusion import composite_alpha
from quant_core.research.backtest import purged_walk_forward_splits
from quant_core.research.flow_backtest import run_flow_alpha_backtest


def test_purged_splits_respect_gap():
    splits = list(purged_walk_forward_splits(500, train_size=200, test_size=50, purge_gap=5))
    assert len(splits) >= 1
    train_idx, test_idx = splits[0]
    assert test_idx.min() >= train_idx.max() + 5


def test_composite_alpha_bounds():
    df = synthetic_ohlcv(400, seed=1)
    # Patch resolve inside composite - uses live path; use_live=False via synthetic chain
    result = composite_alpha("BTC/USDT", use_live=False, window=350)
    assert -1.0 <= result["composite_score"] <= 1.0
    assert result["recommendation"] in {
        "OVERWEIGHT_LONG",
        "OVERWEIGHT_SHORT",
        "NEUTRAL_FLAT",
        "TACTICAL_TILT",
    }


def test_flow_backtest_produces_folds():
    df = synthetic_ohlcv(500, seed=2)
    bt = run_flow_alpha_backtest(df, symbol="BTC/USDT")
    assert "sharpe" in bt.metrics
    assert isinstance(bt.folds, list)
