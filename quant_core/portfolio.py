"""Portfolio optimization with risk budgets and stress scenarios."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from scipy.optimize import minimize


@dataclass
class OptimizationResult:
    weights: dict[str, float]
    expected_return: float
    expected_vol: float
    stress_loss: float
    success: bool


def optimize_portfolio(
    returns: pd.DataFrame,
    *,
    risk_aversion: float = 4.0,
    max_weight: float = 0.45,
    min_weight: float = 0.0,
    stress_shock: float = -0.08,
) -> OptimizationResult:
    cols = list(returns.columns)
    mu = returns.mean().values
    cov = returns.cov().values
    n = len(cols)
    x0 = np.repeat(1.0 / n, n)
    bounds = [(min_weight, max_weight) for _ in range(n)]
    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]

    def objective(w: np.ndarray) -> float:
        ret = float(np.dot(mu, w))
        vol = float(np.sqrt(np.dot(w.T, np.dot(cov, w))))
        return -(ret - risk_aversion * vol)

    opt = minimize(objective, x0=x0, bounds=bounds, constraints=constraints)
    w = opt.x if opt.success else x0
    exp_ret = float(np.dot(mu, w))
    exp_vol = float(np.sqrt(np.dot(w.T, np.dot(cov, w))))
    stress_loss = float(np.dot(np.repeat(stress_shock, n), w))
    return OptimizationResult(
        weights={c: float(v) for c, v in zip(cols, w)},
        expected_return=exp_ret,
        expected_vol=exp_vol,
        stress_loss=stress_loss,
        success=bool(opt.success),
    )


def risk_budget_report(weights: dict[str, float], covariance: pd.DataFrame) -> dict[str, Any]:
    cols = list(weights.keys())
    w = np.array([weights[c] for c in cols])
    cov = covariance.loc[cols, cols].values
    port_vol = float(np.sqrt(np.dot(w.T, np.dot(cov, w)))) + 1e-12
    mrc = np.dot(cov, w) / port_vol
    rc = w * mrc
    return {
        "portfolio_vol": port_vol,
        "risk_contribution": {c: float(v) for c, v in zip(cols, rc)},
    }
