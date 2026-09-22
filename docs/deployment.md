# Deployment

Local / free only:

1. `docker compose up -d` for Postgres (pgvector) + Redis
2. Run FastAPI with uvicorn on :8009
3. Run Next.js on :3009
4. Optional: host Ollama on :11434 and set `LLM_PROVIDER=ollama`

No paid SaaS required for the completion gate.

Production sketch: same containers behind a reverse proxy; rotate `JWT_SECRET`; keep DB names prefixed `rootcause_`.
