# RootCause — AI Debugging Assistant

## Overview

RootCause is an evidence-bound AI software debugging and root-cause assistant. It is **not** a chatbot toy: every important conclusion must cite retrieved evidence from tools and RAG.

## Problem

On-call engineers drown in logs, metrics, deploys, and tribal runbooks. Generic LLM chat invents plausible-sounding causes. RootCause forces a tool → evidence → hypothesis loop with confidence and next investigation steps.

## Stack (free / local only)

| Layer | Choice |
| --- | --- |
| Frontend | Next.js + TypeScript (:3009) |
| API | Python FastAPI (:8009) |
| DB | PostgreSQL + pgvector (:5439) |
| Cache | Redis (:6384) |
| LLM | `LLM_PROVIDER=mock` (default) or `ollama` (Qwen / compatible) |

**No paid AI APIs.**

## Ports

| Service | Port |
| --- | --- |
| Next.js | 3009 |
| FastAPI | 8009 |
| Postgres (pgvector) | 5439 |
| Redis | 6384 |
| Ollama (optional) | 11434 |

## Quick start

```bash
cd 05-ai-debugging-assistant
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local

docker compose up -d

cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/migrate.py --with-test
python scripts/seed.py --with-test

uvicorn app.main:app --host 0.0.0.0 --port 8009 --app-dir .

# other terminal
cd frontend
npm install
npm run dev
```

- UI: http://localhost:3009  
- API docs: http://localhost:8009/docs  
- Demo: `admin@rootcause.local` / `Password123!`

## LLM providers

```bash
# Default for CI / no GPU
LLM_PROVIDER=mock

# Optional local model via Ollama
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b
```

Install Ollama, pull a model (`ollama pull qwen2.5:7b`), set `LLM_PROVIDER=ollama`, restart the API. If Ollama is down, the API falls back to MockLLM automatically.

## Tools

- `search_logs()`
- `get_metrics()`
- `get_recent_deployments()`
- `get_service_dependencies()`
- `search_previous_incidents()`
- `search_runbooks()`

## Tests & evaluation

```bash
cd backend && source .venv/bin/activate
pytest tests/unit -q
pytest tests/integration -q
python scripts/eval.py

cd ../frontend
npm run lint && npm run typecheck && npm run build
```

## Database safety

Only `rootcause` / `rootcause_test` databases are used. Scripts refuse other DB names.

## Docs

See `docs/` for PRD, architecture, API, evaluation, security, and `docs/completion-report.md`.
