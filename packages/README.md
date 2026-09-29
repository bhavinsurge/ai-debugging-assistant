# RootCause packages

RootCause uses PostgreSQL + pgvector with SQL migrations in `apps/api/scripts/migrate.py` (and Docker init under `infrastructure/docker/postgres/`) rather than Prisma.

AI/RAG/tool-calling and the investigation pipeline live inside `apps/api` (FastAPI). A separate `packages/*` TypeScript/Prisma package is not required for this project.
