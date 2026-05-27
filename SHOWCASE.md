# Portfolio showcase guide

Use this project to demonstrate **quant engineering**, **ML**, and **platform engineering** in interviews at top AI/fintech firms.

## Elevator pitch (30 seconds)

> I built Crypto Quant Nexus 3.0 — an institutional crypto quant research platform with **multi-signal alpha fusion**, **purged walk-forward backtests**, a **6-asset universe**, data quality contracts, five specialist analytics modules, Alpha Terminal command center, FastAPI v2 research endpoints, and full CI/MLOps.

## What makes this different from a GitHub clone

| Differentiator | Evidence in repo |
|----------------|------------------|
| Original architecture | `quant_core` shared library + 5 apps + API, not a single notebook |
| Train/serve separation | `quant_core/ml/` used by Streamlit **and** FastAPI |
| Horizon wiring fixed | Flow Alpha UI horizon maps to `shift(-N)` via `horizon_bars_from_label()` |
| DevOps | `.github/workflows/ci.yml` — lint, tests, Docker smoke |
| MLOps | `mlops/training/`, artifacts, optional MLflow, nightly workflow |
| Tests | 18+ pytest cases on BS round-trip, AS spreads, ML pipelines |
| Docs | `ARCHITECTURE.md`, Mermaid diagrams, OpenAPI at `/docs` |

## Resume bullet examples

- Designed and shipped a **multi-service crypto quant platform** (Streamlit + FastAPI + MLflow) with **70%+ test coverage** on core libraries.
- Implemented **MLOps pipelines** for gradient boosting (order flow) and K-Means (regime detection) with **versioned joblib artifacts** and MLflow experiment tracking.
- Built **CI/CD** on GitHub Actions: Ruff lint, pytest, offline model training, and Docker image validation.

## LinkedIn post angle

1. Live demo URL (Streamlit Cloud or Render)
2. Screenshot of Vol Surface 3D + Regime transition matrix
3. Link to `ARCHITECTURE.md` and mention FastAPI `/v1/ml/flow/signal`
4. Tag stack: Python, scikit-learn, FastAPI, Docker, MLflow, CCXT

## Commands to demo in a live interview

```bash
make test          # green CI locally
make train         # produces artifacts/models/
make api           # open localhost:8000/docs
docker compose up  # full stack
```

## Talking points for ML/system design

- **Why gradient boosting for OFI?** Non-linear microstructure features; interpretable importances for research dashboards.
- **Why K-Means for regimes?** Interpretable clusters in vol/momentum space; transition matrix for state analytics.
- **Fallback data chain:** CCXT → Yahoo → deterministic synthetic — demos never break offline.
- **Future work you can articulate:** WebSocket LOB, Feast feature store, shadow deployments for models.
