# Deployment

Local / free only (Yarn monorepo):

1. `yarn infra:up` for Postgres (pgvector :5439) + Redis (:6384)
2. `yarn python:install` then `yarn db:migrate` / `yarn db:seed`
3. `yarn api:dev` — FastAPI on :8009
4. `yarn web:dev` — Next.js on :3009 (rewrites `/api` → FastAPI)
5. Optional: host Ollama on :11434 and set `LLM_PROVIDER=ollama` in `apps/api/.env`

No paid SaaS required for the completion gate.

Production sketch: same containers behind a reverse proxy; rotate `JWT_SECRET`; keep DB names prefixed `rootcause_`.
