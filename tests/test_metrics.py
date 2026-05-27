"""Risk metric edge cases."""

import numpy as np
import pandas as pd

from quant_core.metrics import annualized_vol, max_drawdown, performance_summary, sharpe_ratio, sortino_ratio


def test_sharpe_zero_on_flat_returns():
    returns = pd.Series([0.0, 0.0, 0.0])
    assert sharpe_ratio(returns) == 0.0


def test_max_drawdown_negative():
    equity = pd.Series([100, 110, 90, 95])
    assert max_drawdown(equity) < 0


def test_annualized_vol_positive():
    returns = pd.Series([0.01, -0.02, 0.015, 0.005])
    assert annualized_vol(returns) > 0


def test_performance_summary_keys():
    returns = pd.Series(np.random.default_rng(0).normal(0.0001, 0.01, 100))
    summary = performance_summary(returns)
    assert "sortino" in summary
    assert "calmar" in summary
    assert "hit_rate" in summary


def test_sortino_finite():
    returns = pd.Series([0.01, -0.02, 0.015, 0.005, -0.01])
    assert np.isfinite(sortino_ratio(returns))
