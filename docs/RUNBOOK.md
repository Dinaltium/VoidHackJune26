# Runbook

## Prerequisites

- Python 3.12 (conda env `firewall` recommended)
- Node.js 20+
- A free Groq API key in `.env` at the repo root: `GROQ_API_KEY=gsk_...`
  (the defender runs without it — the deterministic/heuristic layers work
  offline — but the live agent demo and the model-backed layers need it.)

## 1. Backend (defender proxy)

```bash
conda create -y -n firewall python=3.12        # once
conda run -n firewall pip install -r proxy/requirements.txt
conda run -n firewall python -m uvicorn app.main:app --app-dir proxy --port 8000
```

Health check: `curl http://127.0.0.1:8000/health`

## 2. Dashboard

```bash
cd dashboard
npm install
npm run build && npm run start          # http://localhost:3000
# or: npm run dev   (dev mode; use prod build for e2e)
```

Routes: `/` landing · `/console` live feed dashboard · `/mission` Mission Control.

## 3. Live demo

With the defender running on :8000:

```bash
# Through the defender — send_email is blocked, nothing exfiltrates
conda run -n firewall python -m agent.run_attack --task email

# Straight to the provider — the model emails data externally (the breach)
GROQ_API_KEY=gsk_... conda run -n firewall python -m agent.run_attack --task email --direct

# Indirect prompt-injection variant
conda run -n firewall python -m agent.run_attack --task inject
```

Dashboard-only demo (no Groq needed): click **Run demo attack**, or
`curl -X POST http://127.0.0.1:8000/api/demo/run`.

## 4. Checks

```bash
# Backend
cd proxy
conda run -n firewall ruff check .
conda run -n firewall mypy
conda run -n firewall python -m pytest

# Dashboard
cd dashboard
npx biome check .
npx tsc --noEmit
npm run build
npx playwright install chromium    # once
npx playwright test                # needs defender on :8000 for the live test
```

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/v1/chat/completions` | OpenAI-compatible inspected proxy |
| GET | `/events` | SSE stream of decisions |
| GET | `/api/receipts` `/api/receipts/{id}` | signed receipts (+ verification) |
| GET | `/api/policy` `/api/stats` | dashboard data |
| POST | `/api/demo/run` `/api/seed` `/api/reset` | demo helpers |
| GET/POST | `/api/mission/scenarios` · `/api/mission/run` | Mission Control: run an agent governed/ungoverned |
| GET | `/health` | liveness |

## Rotating the key

The dummy key used during development should be rotated. Update `.env`
(`GROQ_API_KEY=...`) and restart the proxy. `.env` is gitignored.
