# Technical Requirements

| Area | Requirement |
| --- | --- |
| Backend | Python 3.11+, FastAPI, psycopg3 |
| Frontend | Next.js 15, TypeScript, Tailwind |
| Database | PostgreSQL 16 + pgvector, DBs `rootcause` / `rootcause_test` only |
| Cache | Redis for tool result caching |
| Embeddings | Deterministic local hasher (384-d) — no paid embed API |
| LLM | `LLM_PROVIDER=mock\|ollama` |
| Auth | JWT Bearer + optional httpOnly cookie |
| Ports | UI 3009, API 8009, PG 5439, Redis 6384 |

## Safety rails

- `assert_safe_database` refuses non-`rootcause*` DB names
- `sanitize_hypothesis_evidence_ids` strips unknown evidence IDs
- MockLLM refuses high-confidence claims without evidence
