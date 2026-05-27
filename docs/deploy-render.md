# Deploy on Render (hub + API split)

Run **two** web services from one repo: Streamlit Nexus Hub and FastAPI. The hub links to the API Swagger UI via `API_DOCS_URL`.

## Option A — Blueprint (recommended)

1. Push this repo to GitHub (`rushi-7388/Crypto-Quant-Nexus` or your fork).
2. Open [Render Dashboard](https://dashboard.render.com) → **New** → **Blueprint**.
3. Connect the repository; Render reads [`render.yaml`](../render.yaml).
4. Apply the blueprint. You get:
   - `cryptoquant-nexus-hub` — Streamlit on port 8501 (Dockerfile)
   - `cryptoquant-nexus-api` — FastAPI on `$PORT` (Dockerfile.api)
5. Wait for both services to go **Live**. The hub receives `API_DOCS_URL` from the API service’s `RENDER_EXTERNAL_URL` (the hub app appends `/docs` if needed).

| Service | Dockerfile | Health check | Public URLs |
|---------|------------|--------------|-------------|
| Hub | `Dockerfile` | `/` | `https://cryptoquant-nexus-hub.onrender.com` |
| API | `Dockerfile.api` | `/health` | `https://cryptoquant-nexus-api.onrender.com` |
| API docs | — | — | `https://cryptoquant-nexus-api.onrender.com/docs` |

> **Free tier:** services spin down after inactivity; first request may take 30–60s.

## Option B — Manual (two services)

### 1. API service

| Setting | Value |
|---------|--------|
| Type | Web Service |
| Runtime | Docker |
| Dockerfile path | `./Dockerfile.api` |
| Health check path | `/health` |

No custom start command required; the image runs Uvicorn on `$PORT`.

### 2. Hub service

| Setting | Value |
|---------|--------|
| Type | Web Service |
| Runtime | Docker |
| Dockerfile path | `./Dockerfile` |
| Health check path | `/` |

**Environment variable:**

| Key | Value |
|-----|--------|
| `API_DOCS_URL` | `https://<your-api-service>.onrender.com` |

The hub normalizes this to `…/docs` automatically.

### 3. Optional — link from API to hub

On the API service, add for documentation only:

| Key | Value |
|-----|--------|
| `HUB_URL` | `https://<your-hub-service>.onrender.com` |

## Verify deployment

```bash
curl https://cryptoquant-nexus-api.onrender.com/health
# {"status":"ok","product":"Crypto Quant Nexus",...}

curl "https://cryptoquant-nexus-api.onrender.com/v1/ml/flow/signal?use_live=false"
```

Open the hub URL and click **Open API docs (Swagger)**.

## CI badge

After the first push to `main`, the README CI badge will show pass/fail:

`https://github.com/rushi-7388/Crypto-Quant-Nexus/actions/workflows/ci.yml`

Forks should update `GITHUB_REPO` and the badge URL in `README.md` and `quant_core/brand.py`.

## MLflow on Render

MLflow is not included in the free two-service blueprint (use `docker compose` locally). For production tracking, add a third Render service or use [MLflow managed hosting](https://mlflow.org/docs/latest/tracking.html).
