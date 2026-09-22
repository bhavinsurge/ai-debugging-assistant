# Database Design

Databases: `rootcause`, `rootcause_test` (port 5439).

## Tables

- `users` — auth
- `documents` / `document_chunks` — RAG corpus with pgvector embeddings
- `service_logs`, `service_metrics`, `deployments`
- `service_dependencies`, `past_incidents`
- `investigations` — status, confidence, JSON report

## Vector index

HNSW cosine index on `document_chunks.embedding` (IVFFlat fallback).

## Safety

Migrations/seeds call `assert_safe_database` and only touch `rootcause*`.
