# Project 5 Completion Report

```text
Project: RootCause — AI Debugging & Root-Cause Assistant
Status: COMPLETE — completion gate passed

Architecture: FastAPI investigation API + Next.js console + PostgreSQL/pgvector RAG
  + Redis tool-cache + MockLLM (default) / optional Ollama
Database: PostgreSQL 16 + pgvector via Docker (host :5439), DBs rootcause / rootcause_test only
Backend: Python FastAPI tools, RAG embeddings, evidence-bound investigation pipeline
Frontend: RootCause console (Fraunces + Source Sans 3 + IBM Plex Mono; moss/signal light UI)

Major features:
- Semantic retrieval over logs/metrics/deploys/incidents/runbooks/architecture docs
- Tools: search_logs, get_metrics, get_recent_deployments, get_service_dependencies,
  search_previous_incidents, search_runbooks
- Evidence collection → structured hypothesis with confidence + investigation steps
- Hard sanitize: LLM cannot cite evidence IDs that were not retrieved
- LLM_PROVIDER=mock|ollama (MockLLM default for CI; Ollama optional)
- Evaluation harness on 6 controlled incidents

Authentication: bcrypt passwords + JWT Bearer (cookie optional)
Authorization: authenticated engineer/admin access to investigations

Testing: Unit 6/6, Integration 3/3, Eval 6/6 gate_pass=true;
  frontend lint + typecheck + production build succeeded

Eval aggregates (MockLLM):
  root_cause_identification: 0.958
  evidence_retrieval: 1.0
  false_diagnosis_avoidance: 1.0
  investigation_quality: 1.0
  pass_rate: 1.0
  gate_pass: true

Security: CORS to UI origin; Pydantic validation; rootcause_* DB guard; evidence ID sanitize
Performance: Redis caches log searches; HNSW vector index on chunks
Deployment: Docker Compose for PG+Redis; uvicorn + Next on host; free/local only

Known limitations:
- Default MockLLM is signature-based (deterministic) — not a general LLM
- Local hash embeddings (not neural) — good enough for seed corpus ranking
- Ollama not installed in this environment; switch via LLM_PROVIDER=ollama when available
- Single-tenant demo auth (no SSO)
- Investigation runs synchronously in the create request (fine for local demo)

Important engineering decisions:
- Isolated ports 3009 / 8009 / 5439 / 6384
- Evidence-first pipeline with sanitize rail regardless of LLM provider
- Controlled incident seed aligned with eval dataset
- Safety scripts refuse non-rootcause databases

Files created: under 05-ai-debugging-assistant/ (docs, docker, backend, frontend)

How to run locally:
  cd 05-ai-debugging-assistant
  cp backend/.env.example backend/.env
  cp frontend/.env.example frontend/.env.local
  docker compose up -d
  cd backend && python3 -m venv .venv && source .venv/bin/activate
  pip install -r requirements.txt
  python scripts/migrate.py --with-test && python scripts/seed.py --with-test
  uvicorn app.main:app --host 0.0.0.0 --port 8009 --app-dir .
  cd ../frontend && npm install && npm run dev   # http://localhost:3009

Demo login: admin@rootcause.local / Password123!

How to run tests:
  cd backend && pytest tests/unit -q && pytest tests/integration -q && python scripts/eval.py
  cd frontend && npm run lint && npm run typecheck && npm run build

How to deploy:
  See docs/deployment.md — Compose + host processes; optional Ollama on :11434.
```
