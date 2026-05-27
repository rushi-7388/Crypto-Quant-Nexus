"""Multi-signal alpha fusion — flow, regime, funding, momentum."""

from __future__ import annotations

from typing import Any

import pandas as pd

from quant_core.data import fetch_funding_rates_demo, resolve_price_feed
from quant_core.ml.flow_model import build_flow_features, predict_flow_signal, train_flow_model
from quant_core.ml.regime_model import train_regime_model
from quant_core.platform.catalog import ASSET_UNIVERSE, list_universe

DEFAULT_WEIGHTS = {
    "flow": 0.35,
    "regime": 0.25,
    "momentum": 0.25,
    "funding": 0.15,
}

REGIME_SCORE_MAP = {
    "Bull Trend": 1.0,
    "Accumulation": 0.35,
    "Bear Trend": -1.0,
    "High Vol / Panic": -0.6,
}


def _momentum_score(df: pd.DataFrame, lookback: int = 20) -> float:
    if len(df) < lookback + 1:
        return 0.0
    ret = df["close"].pct_change(lookback).iloc[-1]
    return float(max(-1.0, min(1.0, ret * 25)))


def _funding_score(symbol: str = "BTC/USDT") -> tuple[float, str]:
    try:
        table = fetch_funding_rates_demo()
        avg = float(table["funding_rate_pct"].mean())
        # Positive funding → crowded longs → slight bearish tilt for spot
        score = float(max(-1.0, min(1.0, -avg * 20)))
        return score, "live_or_synthetic"
    except Exception:
        return 0.0, "unavailable"


def composite_alpha(
    symbol: str = "BTC/USDT",
    use_live: bool = True,
    window: int = 500,
    weights: dict[str, float] | None = None,
    n_regimes: int = 4,
    horizon_bars: int = 3,
) -> dict[str, Any]:
    """
    Fuse microstructure ML, regime state, momentum, and funding into one conviction score.
    Returns score in [-1, 1] and actionable recommendation.
    """
    w = {**DEFAULT_WEIGHTS, **(weights or {})}
    total_w = sum(w.values()) or 1.0
    w = {k: v / total_w for k, v in w.items()}

    df, feed = resolve_price_feed(symbol, use_live=use_live)
    df = df.tail(window).copy()

    flow_art = train_flow_model(df, horizon_bars=horizon_bars)
    featured = build_flow_features(df).dropna(subset=list(flow_art.features))
    flow_sig = predict_flow_signal(flow_art, featured)
    flow_score = float(flow_sig["probability_up"] * 2 - 1)

    regime_art, labeled = train_regime_model(df, n_regimes=n_regimes)
    regime_name = str(labeled["regime_name"].dropna().iloc[-1])
    regime_score = REGIME_SCORE_MAP.get(regime_name, 0.0)

    mom_score = _momentum_score(df)
    fund_score, fund_src = _funding_score(symbol)

    composite = (
        w["flow"] * flow_score
        + w["regime"] * regime_score
        + w["momentum"] * mom_score
        + w["funding"] * fund_score
    )
    composite = float(max(-1.0, min(1.0, composite)))
    conviction = abs(composite)

    if composite > 0.35:
        action = "OVERWEIGHT_LONG"
    elif composite < -0.35:
        action = "OVERWEIGHT_SHORT"
    elif conviction < 0.15:
        action = "NEUTRAL_FLAT"
    else:
        action = "TACTICAL_TILT"

    meta = ASSET_UNIVERSE.get(symbol, {})
    return {
        "symbol": symbol,
        "feed": feed,
        "composite_score": round(composite, 4),
        "conviction": round(conviction, 4),
        "recommendation": action,
        "components": {
            "flow": {"score": round(flow_score, 4), "signal": flow_sig["signal"], "weight": w["flow"]},
            "regime": {"score": round(regime_score, 4), "name": regime_name, "weight": w["regime"]},
            "momentum": {"score": round(mom_score, 4), "weight": w["momentum"]},
            "funding": {"score": round(fund_score, 4), "source": fund_src, "weight": w["funding"]},
        },
        "asset_meta": meta,
        "model_accuracy": flow_art.accuracy,
    }


def fuse_multi_asset(
    symbols: list[str] | None = None,
    use_live: bool = True,
    top_n: int = 5,
) -> pd.DataFrame:
    """Rank universe by composite alpha conviction."""
    syms = symbols or list_universe()
    rows = []
    for sym in syms:
        try:
            result = composite_alpha(sym, use_live=use_live)
            rows.append(
                {
                    "symbol": sym,
                    "composite_score": result["composite_score"],
                    "conviction": result["conviction"],
                    "recommendation": result["recommendation"],
                    "flow_signal": result["components"]["flow"]["signal"],
                    "regime": result["components"]["regime"]["name"],
                }
            )
        except Exception:
            continue
    ranked = pd.DataFrame(rows).sort_values("composite_score", ascending=False)
    return ranked.head(top_n).reset_index(drop=True)
