# Forward-Deployed Architecture (v4.1)

This project now includes a practical Forward Deployed Engineer stack:

## 1) Feature Store + Online/Offline Parity
- Contracts: `mlops/contracts/features.yaml`
- Runtime parity checker: `quant_core/feature_store.py`
- API: `GET /v2/features/parity`

## 2) Shadow Rollout + Canary Scoring
- Router: `quant_core/shadow.py`
- API: `GET /v2/alpha/shadow`
- Compares primary and shadow alpha models and reports divergence.

## 3) Event-Driven Inference
- Event primitives: `quant_core/eventing.py`
- Worker: `worker/inference_worker.py`
- Queue endpoint: `POST /v2/events/inference-request`
- Local infra: Redpanda in `docker-compose.yml`.

## 4) Execution Simulation
- Engine: `quant_core/execution.py`
- API: `POST /v2/execution/simulate`
- Models spread, slippage, fees, latency.

## 5) Portfolio Optimizer
- Engine: `quant_core/portfolio.py`
- API: `GET /v2/portfolio/optimize`
- Includes constrained allocation + stress shock + risk budget.

## 6) Observability + Audit Trail
- Trace propagation: `quant_core/observability.py`
- Decision audit: `quant_core/audit.py`
- API middleware emits `x-trace-id` on responses.
- Audit log written to `artifacts/audit/decisions.jsonl`.

## 7) LLM Quant Copilot + RAG (v4.1)
- Package: `quant_core/copilot/`
- Indexes audit, events, model cards, and backtest snapshots.
- API: `GET /v2/copilot/status`, `POST /v2/copilot/index`, `POST /v2/copilot/ask`
- UI: Ops Dashboard + Nexus Hub
- Docs: [COPILOT.md](./COPILOT.md)

## Run full stack
```bash
docker compose up --build
```

Services:
- Hub/UI: `http://localhost:8501`
- API docs: `http://localhost:8000/docs`
- MLflow: `http://localhost:5000`
- Redpanda Kafka: `localhost:9092`
