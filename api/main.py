"""FastAPI service — quant analytics and ML inference without Streamlit."""

from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, Query
from pydantic import BaseModel, Field

from quant_core.brand import AUTHOR, BRAND, VERSION
from quant_core.data import fetch_funding_rates_demo, resolve_price_feed
from quant_core.logging_config import configure_logging
from quant_core.metrics import annualized_vol, max_drawdown, performance_summary, sharpe_ratio
from quant_core.ml.model_card import flow_alpha_model_card, regime_nexus_model_card
from quant_core.ml.flow_model import (
    build_flow_features,
    horizon_bars_from_label,
    load_flow_artifact,
    predict_flow_signal,
    train_flow_model,
)
from quant_core.ml.regime_model import (
    detect_regimes,
    load_regime_artifact,
    train_regime_model,
    transition_matrix,
)
from quant_core.options import black_scholes_price, greeks, implied_volatility
from quant_core.platform.catalog import ASSET_UNIVERSE, list_universe
from quant_core.platform.quality import ohlcv_quality_report
from quant_core.research.alpha_fusion import composite_alpha, fuse_multi_asset
from quant_core.research.flow_backtest import run_flow_alpha_backtest

configure_logging(service_name="crypto-quant-api")
app = FastAPI(
    title="Crypto Quant Nexus API",
    description=(
        "Institutional crypto quant API — market data, options, ML signals, "
        "multi-signal alpha fusion, walk-forward backtests, and data quality."
    ),
    version=VERSION,
)


class HealthResponse(BaseModel):
    status: str
    product: str
    version: str
    author: str


class GreeksRequest(BaseModel):
    spot: float = Field(..., gt=0)
    strike: float = Field(..., gt=0)
    maturity_years: float = Field(..., gt=0)
    rate: float = 0.0
    volatility: float = Field(..., gt=0)
    option_type: str = "call"


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    return HealthResponse(status="ok", product=BRAND, version=VERSION, author=AUTHOR)


@app.get("/v1/ohlcv", tags=["market-data"])
def ohlcv(
    symbol: str = Query("BTC/USDT"),
    use_live: bool = Query(True),
    limit: int = Query(300, ge=50, le=2000),
) -> dict[str, Any]:
    df, label = resolve_price_feed(symbol, use_live=use_live)
    tail = df.tail(limit)
    return {
        "symbol": symbol,
        "feed": label,
        "rows": len(tail),
        "data": tail.assign(timestamp=tail["timestamp"].astype(str)).to_dict(orient="records"),
    }


@app.get("/v1/funding", tags=["market-data"])
def funding() -> dict[str, Any]:
    table = fetch_funding_rates_demo()
    return {"rows": len(table), "venues": table.to_dict(orient="records")}


@app.get("/v1/metrics/risk", tags=["analytics"])
def risk_metrics(symbol: str = Query("BTC/USDT"), use_live: bool = Query(True)) -> dict[str, float]:
    df, _ = resolve_price_feed(symbol, use_live=use_live)
    returns = df["close"].pct_change().dropna()
    return performance_summary(returns)


@app.get("/v2/universe", tags=["platform"])
def universe() -> dict[str, Any]:
    return {
        "count": len(ASSET_UNIVERSE),
        "assets": [
            {"symbol": sym, **meta} for sym, meta in ASSET_UNIVERSE.items()
        ],
    }


@app.get("/v2/data/quality", tags=["platform"])
def data_quality(
    symbol: str = Query("BTC/USDT"),
    use_live: bool = Query(True),
    limit: int = Query(500, ge=100, le=2000),
) -> dict[str, Any]:
    df, feed = resolve_price_feed(symbol, use_live=use_live)
    report = ohlcv_quality_report(df.tail(limit))
    return {"symbol": symbol, "feed": feed, **report}


@app.get("/v2/alpha/composite", tags=["research"])
def alpha_composite(
    symbol: str = Query("BTC/USDT"),
    use_live: bool = Query(True),
    window: int = Query(500, ge=200, le=1000),
) -> dict[str, Any]:
    return composite_alpha(symbol, use_live=use_live, window=window)


@app.get("/v2/alpha/universe-rank", tags=["research"])
def alpha_universe_rank(
    use_live: bool = Query(True),
    top_n: int = Query(6, ge=1, le=10),
) -> dict[str, Any]:
    ranked = fuse_multi_asset(symbols=list_universe(), use_live=use_live, top_n=top_n)
    return {"rows": len(ranked), "rankings": ranked.to_dict(orient="records")}


@app.get("/v2/research/backtest/flow", tags=["research"])
def backtest_flow(
    symbol: str = Query("BTC/USDT"),
    use_live: bool = Query(True),
    window: int = Query(500, ge=300, le=1000),
) -> dict[str, Any]:
    df, feed = resolve_price_feed(symbol, use_live=use_live)
    result = run_flow_alpha_backtest(df.tail(window), symbol=symbol)
    return {
        "symbol": symbol,
        "feed": feed,
        "metrics": result.metrics,
        "folds": result.folds,
        "oos_points": len(result.equity_curve),
    }


@app.get("/v2/ml/model-cards", tags=["machine-learning"])
def model_cards() -> dict[str, Any]:
    import json
    from pathlib import Path

    flow_meta, regime_meta = {}, {}
    flow_path = Path("artifacts/models/flow_alpha/metadata.json")
    regime_path = Path("artifacts/models/regime_nexus/metadata.json")
    if flow_path.exists():
        flow_meta = json.loads(flow_path.read_text(encoding="utf-8"))
    if regime_path.exists():
        regime_meta = json.loads(regime_path.read_text(encoding="utf-8"))
    return {
        "flow_alpha": flow_alpha_model_card(flow_meta),
        "regime_nexus": regime_nexus_model_card(regime_meta),
    }


@app.post("/v1/options/greeks", tags=["options"])
def option_greeks(body: GreeksRequest) -> dict[str, float]:
    return greeks(
        body.spot,
        body.strike,
        body.maturity_years,
        body.rate,
        body.volatility,
        body.option_type,
    )


@app.get("/v1/options/iv", tags=["options"])
def option_iv(
    market_price: float = Query(..., gt=0),
    spot: float = Query(..., gt=0),
    strike: float = Query(..., gt=0),
    maturity_years: float = Query(..., gt=0),
    rate: float = 0.0,
    option_type: str = "call",
) -> dict[str, float]:
    iv = implied_volatility(market_price, spot, strike, maturity_years, rate, option_type)
    model_price = black_scholes_price(spot, strike, maturity_years, rate, iv, option_type)
    return {"implied_volatility": iv, "model_price": model_price}


@app.get("/v1/ml/flow/signal", tags=["machine-learning"])
def flow_signal(
    symbol: str = Query("BTC/USDT"),
    horizon: str = Query("3 bars"),
    use_live: bool = Query(True),
    train_window: int = Query(400, ge=200, le=800),
) -> dict[str, Any]:
    artifact = load_flow_artifact()
    df, feed = resolve_price_feed(symbol, use_live=use_live)
    df = df.tail(train_window)

    if artifact is None or artifact.horizon_bars != horizon_bars_from_label(horizon):
        artifact = train_flow_model(df, horizon_bars=horizon_bars_from_label(horizon))

    featured = build_flow_features(df)
    featured["target"] = (
        featured["close"].shift(-artifact.horizon_bars) > featured["close"]
    ).astype(int)
    featured = featured.dropna()
    signal = predict_flow_signal(artifact, featured)
    return {
        "symbol": symbol,
        "feed": feed,
        "accuracy": artifact.accuracy,
        "artifact_loaded": load_flow_artifact() is not None,
        **signal,
    }


@app.get("/v1/ml/regime/current", tags=["machine-learning"])
def regime_current(
    symbol: str = Query("BTC/USDT"),
    n_regimes: int = Query(4, ge=2, le=6),
    use_live: bool = Query(True),
) -> dict[str, Any]:
    artifact = load_regime_artifact()
    df, feed = resolve_price_feed(symbol, use_live=use_live)
    df = df.tail(600)

    if artifact is None or artifact.n_regimes != n_regimes:
        artifact, labeled = train_regime_model(df, n_regimes=n_regimes)
    else:
        labeled = detect_regimes(artifact, df)

    current_row = labeled.dropna(subset=["regime"]).iloc[-1]
    returns = labeled["ret"].dropna()
    return {
        "symbol": symbol,
        "feed": feed,
        "current_regime": str(current_row["regime_name"]),
        "regime_id": int(current_row["regime"]),
        "annualized_vol": annualized_vol(returns),
        "sharpe": sharpe_ratio(returns),
        "transition_matrix": transition_matrix(labeled.dropna(subset=["regime"])).to_dict(),
        "artifact_loaded": load_regime_artifact() is not None,
    }


@app.get("/v1/ml/models", tags=["machine-learning"])
def list_models() -> dict[str, Any]:
    flow = load_flow_artifact()
    regime = load_regime_artifact()
    return {
        "flow_alpha": {
            "loaded": flow is not None,
            "horizon_bars": flow.horizon_bars if flow else None,
            "accuracy": flow.accuracy if flow else None,
        },
        "regime_nexus": {
            "loaded": regime is not None,
            "n_regimes": regime.n_regimes if regime else None,
        },
        "mlflow_uri": os.getenv("MLFLOW_TRACKING_URI"),
    }


def run() -> None:
    import uvicorn

    port = int(os.getenv("PORT", os.getenv("API_PORT", "8000")))
    uvicorn.run("api.main:app", host="0.0.0.0", port=port, reload=False)


if __name__ == "__main__":
    run()
