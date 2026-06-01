# LLM Quant Copilot (v4.1)

RAG layer over platform governance and research artifacts.

## Indexed sources

| Source | Location |
|--------|----------|
| Decision audit | `artifacts/audit/decisions.jsonl` |
| Inference events | `artifacts/events/*.jsonl` |
| Model cards | `artifacts/models/*/metadata.json` |
| Backtest snapshots | `artifacts/research/backtests.jsonl` + `artifacts/research/*.json` |

## API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/v2/copilot/status` | Index stats and active LLM provider |
| POST | `/v2/copilot/index` | Rebuild lexical index |
| POST | `/v2/copilot/ask` | `{ "question": "...", "top_k": 5 }` |

## LLM providers

Set `COPILOT_LLM_PROVIDER`:

| Value | Behavior |
|-------|----------|
| `mock` (default) | Deterministic summary from retrieved chunks — used in CI |
| `ollama` | `OLLAMA_BASE_URL`, `OLLAMA_MODEL` (default `llama3.2`) |
| `openai` | `OPENAI_API_KEY`, optional `OPENAI_MODEL` |

On provider failure, answers fall back to `mock`.

## UI

- **Ops Dashboard** — full copilot panel (index + ask)
- **Nexus Hub** — same panel when API is reachable (`API_BASE_URL`)

## Local usage

```bash
uvicorn api.main:app --port 8000
curl -X POST http://localhost:8000/v2/copilot/index
curl -X POST http://localhost:8000/v2/copilot/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Is the audit chain healthy? What is latest BTC Sharpe?"}'
```

Backtests run via `GET /v2/research/backtest/flow` are appended to `artifacts/research/backtests.jsonl` for indexing.
