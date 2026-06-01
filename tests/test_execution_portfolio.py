"""Execution simulator and portfolio optimizer tests."""

import numpy as np
import pandas as pd

from quant_core.execution import simulate_execution
from quant_core.portfolio import optimize_portfolio


def test_execution_cost_positive():
    report = simulate_execution(side="buy", quantity=2.0, mid_price=100.0)
    assert report.total_cost > 0
    assert report.fill_price > report.mid_price


def test_portfolio_optimization_weights_sum_one():
    rng = np.random.default_rng(42)
    returns = pd.DataFrame(
        {
            "BTC/USDT": rng.normal(0.0002, 0.01, 300),
            "ETH/USDT": rng.normal(0.00025, 0.012, 300),
            "SOL/USDT": rng.normal(0.0003, 0.018, 300),
        }
    )
    opt = optimize_portfolio(returns)
    assert abs(sum(opt.weights.values()) - 1.0) < 1e-6
