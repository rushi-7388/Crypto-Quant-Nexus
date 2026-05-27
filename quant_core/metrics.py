"""Portfolio and market risk metrics — institutional analytics suite."""

from __future__ import annotations

import numpy as np
import pandas as pd

DEFAULT_PERIODS_PER_YEAR = 252 * 24 * 12  # 5-minute bars


def sharpe_ratio(returns: pd.Series, periods_per_year: float = DEFAULT_PERIODS_PER_YEAR) -> float:
    r = returns.dropna()
    if len(r) < 2 or r.std() == 0:
        return 0.0
    return float(np.sqrt(periods_per_year) * r.mean() / r.std())


def sortino_ratio(
    returns: pd.Series,
    periods_per_year: float = DEFAULT_PERIODS_PER_YEAR,
    mar: float = 0.0,
) -> float:
    """Sharpe using downside deviation only (Sortino)."""
    r = returns.dropna()
    if len(r) < 2:
        return 0.0
    downside = r[r < mar]
    if len(downside) < 2 or downside.std() == 0:
        return 0.0
    return float(np.sqrt(periods_per_year) * (r.mean() - mar) / downside.std())


def max_drawdown(equity: pd.Series) -> float:
    peak = equity.cummax()
    dd = (equity - peak) / peak.replace(0, np.nan)
    return float(dd.min()) if len(dd) else 0.0


def annualized_vol(returns: pd.Series, periods_per_year: float = DEFAULT_PERIODS_PER_YEAR) -> float:
    r = returns.dropna()
    if len(r) < 2:
        return 0.0
    return float(r.std() * np.sqrt(periods_per_year))


def calmar_ratio(
    returns: pd.Series,
    periods_per_year: float = DEFAULT_PERIODS_PER_YEAR,
) -> float:
    """CAGR / |max drawdown| on compounded equity."""
    r = returns.dropna()
    if len(r) < 2:
        return 0.0
    equity = (1 + r).cumprod()
    mdd = abs(max_drawdown(equity))
    if mdd < 1e-12:
        return 0.0
    years = len(r) / periods_per_year
    if years <= 0:
        return 0.0
    cagr = float(equity.iloc[-1] ** (1 / years) - 1)
    return cagr / mdd


def hit_rate(returns: pd.Series) -> float:
    r = returns.dropna()
    if len(r) == 0:
        return 0.0
    return float((r > 0).mean())


def profit_factor(returns: pd.Series) -> float:
    r = returns.dropna()
    gains = r[r > 0].sum()
    losses = abs(r[r < 0].sum())
    if losses < 1e-12:
        return float("inf") if gains > 0 else 0.0
    return float(gains / losses)


def performance_summary(
    returns: pd.Series,
    periods_per_year: float = DEFAULT_PERIODS_PER_YEAR,
) -> dict[str, float]:
    """Single dict of institutional risk/return stats."""
    r = returns.dropna()
    equity = (1 + r).cumprod() if len(r) else pd.Series(dtype=float)
    return {
        "sharpe": sharpe_ratio(r, periods_per_year),
        "sortino": sortino_ratio(r, periods_per_year),
        "annualized_vol": annualized_vol(r, periods_per_year),
        "max_drawdown": max_drawdown(equity) if len(equity) else 0.0,
        "calmar": calmar_ratio(r, periods_per_year),
        "hit_rate": hit_rate(r),
        "profit_factor": profit_factor(r),
        "total_return": float(equity.iloc[-1] - 1) if len(equity) else 0.0,
    }
