# Research methodology — Crypto Quant Nexus 3.0

## Alpha fusion

Composite score ∈ [-1, 1] combines:

| Signal | Weight (default) | Source |
|--------|------------------|--------|
| Flow (OFI + GBC) | 35% | `quant_core/ml/flow_model.py` |
| Regime (K-Means) | 25% | `quant_core/ml/regime_model.py` |
| Momentum (20-bar) | 25% | Price action |
| Funding carry | 15% | Cross-venue CCXT snapshot |

Recommendations: `OVERWEIGHT_LONG`, `OVERWEIGHT_SHORT`, `TACTICAL_TILT`, `NEUTRAL_FLAT`.

Configure weights in `mlops/configs/fusion_weights.yaml`.

## Walk-forward backtesting

- **Purged gaps** between train/test to reduce label leakage (see `purged_walk_forward_splits`).
- **Flow Alpha backtest** retrains gradient boosting each fold; OOS positions from probability thresholds (0.55 / 0.45).
- Metrics: Sharpe, Sortino, Calmar, max drawdown, hit rate, profit factor.

API: `GET /v2/research/backtest/flow`

## Data platform

- **Universe:** 6 L1 crypto perpetuals (`quant_core/platform/catalog.py`).
- **Parquet cache:** `artifacts/data/cache/` for reproducible research.
- **Quality contract:** schema, gaps, spikes (`ohlcv_quality_report`).

## Model governance

- Model cards: `GET /v2/ml/model-cards`
- Artifacts: `artifacts/models/`
- MLflow (optional): set `MLFLOW_TRACKING_URI`

## Disclaimer

Research and education only. Past simulated performance does not guarantee future results.
