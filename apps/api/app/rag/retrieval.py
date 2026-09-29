from __future__ import annotations

from typing import Any

from app.db.session import get_conn
from app.rag.embeddings import embed_text, to_pgvector_literal


def search_documents(
    *,
    query: str,
    doc_types: list[str] | None = None,
    limit: int = 8,
    database_url: str | None = None,
) -> list[dict[str, Any]]:
    """Semantic retrieval over document_chunks via pgvector cosine distance."""
    vector = embed_text(query)
    literal = to_pgvector_literal(vector)
    types = doc_types or ["runbook", "architecture", "incident", "log", "metric", "deploy"]

    sql = """
        SELECT
            d.id AS document_id,
            d.doc_type,
            d.title,
            d.service,
            d.source_ref,
            c.id AS chunk_id,
            c.chunk_index,
            c.content,
            1 - (c.embedding <=> %s::vector) AS score
        FROM document_chunks c
        JOIN documents d ON d.id = c.document_id
        WHERE d.doc_type = ANY(%s)
        ORDER BY c.embedding <=> %s::vector
        LIMIT %s
    """
    with get_conn(database_url) as conn:
        rows = conn.execute(sql, (literal, types, literal, limit)).fetchall()
    return [dict(r) for r in rows]


def rank_by_relevance(query: str, candidates: list[dict[str, Any]], text_key: str = "content") -> list[dict[str, Any]]:
    """Re-rank in-memory candidates by embedding cosine (unit-testable without DB)."""
    from app.rag.embeddings import cosine_similarity, embed_text

    q = embed_text(query)
    scored: list[dict[str, Any]] = []
    for item in candidates:
        text = str(item.get(text_key) or item.get("summary") or "")
        score = cosine_similarity(q, embed_text(text))
        enriched = dict(item)
        enriched["relevance"] = score
        scored.append(enriched)
    scored.sort(key=lambda x: x.get("relevance", 0.0), reverse=True)
    return scored
