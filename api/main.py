"""FastAPI service — quant analytics and ML inference without Streamlit."""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, Query, Request
from pydantic import BaseModel, Field

from quant_core.audit import append_decision_audit, verify_audit_chain
from quant_core.brand import AUTHOR, BRAND, VERSION
from quant_core.canary import apply_canary_update, load_canary_state
from quant_core.copilot.service import ask as copilot_ask
from quant_core.copilot.service import copilot_status, rebuild_index as copilot_rebuild_index
from quant_core.data import fetch_funding_rates_demo, resolve_price_feed
from quant_core.eventing import kafka_publish
from quant_core.events_store import REQUEST_LOG, append_event, dashboard_snapshot
from quant_core.execution import simulate_execution
from quant_core.feature_store import parity_report
from quant_core.logging_config import configure_logging
from quant_core.metrics import annualized_vol, performance_summary, sharpe_ratio
from quant_core.ml.flow_model import (
    build_flow_features,
    horizon_bars_from_label,
    load_flow_artifact,
    predict_flow_signal,
    train_flow_model,
)
from quant_core.ml.model_card import flow_alpha_model_card, regime_nexus_model_card
from quant_core.ml.regime_model import (
    detect_regimes,
    load_regime_artifact,
    train_regime_model,
    transition_matrix,
)
from quant_core.observability import current_trace_id, end_trace, start_trace
from quant_core.options import black_scholes_price, greeks, implied_volatility
from quant_core.platform.catalog import ASSET_UNIVERSE, list_universe
from quant_core.platform.quality import ohlcv_quality_report
from quant_core.portfolio import optimize_portfolio, risk_budget_report
from quant_core.research.alpha_fusion import composite_alpha, fuse_multi_asset
from quant_core.research.backtest_store import persist_backtest_snapshot
from quant_core.research.flow_backtest import run_flow_alpha_backtest
from quant_core.shadow import route_with_shadow

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


class ExecutionRequest(BaseModel):
    side: str
    quantity: float = Field(..., gt=0)
    mid_price: float = Field(..., gt=0)
    spread_bps: float = 5.0
    fee_bps: float = 2.0
    slippage_bps_per_unit: float = 0.25
    latency_ms: float = 25.0


class CanaryMetricsRequest(BaseModel):
    avg_divergence: float = Field(..., ge=0.0, le=5.0)
    shadow_win_rate: float = Field(..., ge=0.0, le=1.0)
    samples: int = Field(..., ge=0, le=1_000_000)


class CopilotAskRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=4000)
    top_k: int = Field(5, ge=1, le=15)


@app.middleware("http")
async def trace_middleware(request: Request, call_next):
    incoming = request.headers.get("x-trace-id")
    ctx = start_trace(incoming or str(uuid.uuid4()))
    response = await call_next(request)
    duration_ms = int(end_trace(ctx) * 1000)
    response.headers["x-trace-id"] = ctx.trace_id
    response.headers["x-latency-ms"] = str(duration_ms)
    return response


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
    trace_id = current_trace_id()
    result = composite_alpha(symbol, use_live=use_live, window=window)
    audit = append_decision_audit(
        trace_id=trace_id,
        symbol=symbol,
        model_version="alpha_fusion_v1",
        dataset_version="market_feed_v1",
        decision={
            "composite_score": result["composite_score"],
            "recommendation": result["recommendation"],
        },
        rationale=result["components"],
    )
    return {**result, "trace_id": trace_id, "audit_hash": audit["decision_hash"]}


@app.get("/v2/features/parity", tags=["platform"])
def features_parity(
    symbol: str = Query("BTC/USDT"),
    tolerance: float = Query(0.35, ge=0.01, le=2.0),
) -> dict[str, Any]:
    return parity_report(symbol=symbol, tolerance=tolerance)


@app.get("/v2/alpha/shadow", tags=["research"])
def alpha_shadow(
    symbol: str = Query("BTC/USDT"),
    canary_rate: float = Query(0.1, ge=0.0, le=1.0),
) -> dict[str, Any]:
    trace_id = current_trace_id()
    shadow = route_with_shadow(
        trace_id=trace_id,
        primary_fn=lambda: composite_alpha(symbol=symbol, use_live=True),
        shadow_fn=lambda: composite_alpha(
            symbol=symbol,
            use_live=False,
            weights={"flow": 0.40, "regime": 0.25, "momentum": 0.20, "funding": 0.15},
        ),
        canary_rate=canary_rate,
    )
    return {
        "trace_id": trace_id,
        "routed_to_shadow": shadow.routed_to_shadow,
        "divergence": shadow.divergence,
        "primary": shadow.primary,
        "shadow": shadow.shadow,
    }


@app.post("/v2/events/inference-request", tags=["eventing"])
async def enqueue_inference_request(
    symbol: str = Query("BTC/USDT"),
    use_live: bool = Query(True),
    window: int = Query(500, ge=200, le=1000),
) -> dict[str, Any]:
    trace_id = current_trace_id()
    bootstrap = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    topic = os.getenv("KAFKA_TOPIC_INFERENCE_REQUEST", "inference.requests")
    payload = {"trace_id": trace_id, "symbol": symbol, "use_live": use_live, "window": window}
    append_event(
        REQUEST_LOG,
        {
            **payload,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        },
    )
    try:
        await kafka_publish(topic=topic, bootstrap_servers=bootstrap, payload=payload)
        return {"queued": True, "trace_id": trace_id, "topic": topic}
    except Exception as exc:
        return {"queued": False, "trace_id": trace_id, "error": str(exc)}


@app.get("/v2/events/dashboard", tags=["eventing"])
def events_dashboard() -> dict[str, Any]:
    return dashboard_snapshot()


@app.get("/v2/canary/status", tags=["research"])
def canary_status() -> dict[str, Any]:
    return load_canary_state()


@app.post("/v2/canary/evaluate", tags=["research"])
def canary_evaluate(body: CanaryMetricsRequest) -> dict[str, Any]:
    return apply_canary_update(
        avg_divergence=body.avg_divergence,
        shadow_win_rate=body.shadow_win_rate,
        samples=body.samples,
    )


@app.get("/v2/audit/verify", tags=["platform"])
def audit_verify() -> dict[str, Any]:
    return verify_audit_chain()


@app.get("/v2/copilot/status", tags=["copilot"])
def copilot_status_endpoint() -> dict[str, Any]:
    return copilot_status()


@app.post("/v2/copilot/index", tags=["copilot"])
def copilot_index() -> dict[str, Any]:
    return copilot_rebuild_index()


@app.post("/v2/copilot/ask", tags=["copilot"])
def copilot_ask_endpoint(body: CopilotAskRequest) -> dict[str, Any]:
    result = copilot_ask(body.question, top_k=body.top_k)
    return {
        "answer": result.answer,
        "sources": result.sources,
        "provider": result.provider,
        "trace_id": result.trace_id,
        "chunks_used": result.chunks_used,
    }


@app.post("/v2/execution/simulate", tags=["execution"])
def execution_simulate(body: ExecutionRequest) -> dict[str, Any]:
    report = simulate_execution(
        side=body.side.lower(),  # type: ignore[arg-type]
        quantity=body.quantity,
        mid_price=body.mid_price,
        spread_bps=body.spread_bps,
        fee_bps=body.fee_bps,
        slippage_bps_per_unit=body.slippage_bps_per_unit,
        latency_ms=body.latency_ms,
    )
    return report.__dict__


@app.get("/v2/portfolio/optimize", tags=["portfolio"])
def portfolio_optimize(
    symbols: str = Query("BTC/USDT,ETH/USDT,SOL/USDT"),
    use_live: bool = Query(False),
    window: int = Query(400, ge=200, le=1000),
) -> dict[str, Any]:
    chosen = [s.strip() for s in symbols.split(",") if s.strip()]
    series = {}
    for sym in chosen:
        df, _ = resolve_price_feed(sym, use_live=use_live)
        series[sym] = df["close"].pct_change().tail(window).reset_index(drop=True)
    import pandas as pd

    rets = pd.DataFrame(series).dropna()
    if rets.empty or len(rets.columns) < 2:
        return {"error": "not_enough_data", "symbols": chosen}
    opt = optimize_portfolio(rets)
    rb = risk_budget_report(opt.weights, rets.cov())
    return {
        "symbols": chosen,
        "weights": opt.weights,
        "expected_return": opt.expected_return,
        "expected_vol": opt.expected_vol,
        "stress_loss": opt.stress_loss,
        "optimizer_success": opt.success,
        "risk_budget": rb,
    }


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
    payload = {
        "symbol": symbol,
        "feed": feed,
        "metrics": result.metrics,
        "folds": result.folds,
        "oos_points": len(result.equity_curve),
    }
    persist_backtest_snapshot(
        symbol=symbol,
        feed=feed,
        metrics=result.metrics,
        folds=result.folds,
        oos_points=len(result.equity_curve),
        source="api",
    )
    return payload


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
