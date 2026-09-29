from __future__ import annotations

import json
from typing import Any

from app.db.session import get_conn
from app.rag.retrieval import search_documents


def _cache_get(redis_client: Any, key: str) -> Any | None:
    if redis_client is None:
        return None
    try:
        raw = redis_client.get(key)
        if raw:
            return json.loads(raw)
    except Exception:
        return None
    return None


def _cache_set(redis_client: Any, key: str, value: Any, ttl: int) -> None:
    if redis_client is None:
        return
    try:
        redis_client.setex(key, ttl, json.dumps(value, default=str))
    except Exception:
        return


def search_logs(
    *,
    query: str,
    service: str | None = None,
    limit: int = 10,
    database_url: str | None = None,
    redis_client: Any = None,
    cache_ttl: int = 120,
) -> list[dict[str, Any]]:
    cache_key = f"tool:search_logs:{service}:{query}:{limit}"
    cached = _cache_get(redis_client, cache_key)
    if cached is not None:
        return cached

    semantic = search_documents(
        query=query,
        doc_types=["log"],
        limit=limit,
        database_url=database_url,
    )
    results: list[dict[str, Any]] = []
    for row in semantic:
        if service and row.get("service") and row["service"] != service:
            continue
        results.append(
            {
                "id": f"log:{row['chunk_id']}",
                "source": "logs",
                "tool": "search_logs",
                "summary": row["content"][:400],
                "raw": {
                    "document_id": str(row["document_id"]),
                    "chunk_id": str(row["chunk_id"]),
                    "title": row["title"],
                    "service": row.get("service"),
                    "score": float(row["score"]),
                },
                "relevance": float(row["score"]),
            }
        )

    # Structured log table fallback / enrichment
    with get_conn(database_url) as conn:
        sql = """
            SELECT id, service, level, message, occurred_at, metadata
            FROM service_logs
            WHERE (%s::text IS NULL OR service = %s)
              AND (
                message ILIKE '%%' || %s || '%%'
                OR COALESCE(metadata->>'error_code', '') ILIKE '%%' || %s || '%%'
              )
            ORDER BY occurred_at DESC
            LIMIT %s
        """
        tokens = [t for t in query.replace(",", " ").split() if len(t) > 2][:3]
        needle = tokens[0] if tokens else query[:40]
        rows = conn.execute(sql, (service, service, needle, needle, limit)).fetchall()
        for r in rows:
            eid = f"slog:{r['id']}"
            if any(x["id"] == eid for x in results):
                continue
            results.append(
                {
                    "id": eid,
                    "source": "logs",
                    "tool": "search_logs",
                    "summary": f"[{r['level']}] {r['service']}: {r['message']}",
                    "raw": {
                        "id": str(r["id"]),
                        "service": r["service"],
                        "level": r["level"],
                        "occurred_at": r["occurred_at"].isoformat(),
                        "metadata": r["metadata"] or {},
                    },
                    "relevance": 0.55,
                }
            )

    results = results[:limit]
    _cache_set(redis_client, cache_key, results, cache_ttl)
    return results


def get_metrics(
    *,
    service: str | None = None,
    metric_names: list[str] | None = None,
    limit: int = 20,
    database_url: str | None = None,
) -> list[dict[str, Any]]:
    names = metric_names or []
    with get_conn(database_url) as conn:
        sql = """
            SELECT id, service, metric_name, value, unit, recorded_at, labels
            FROM service_metrics
            WHERE (%s::text IS NULL OR service = %s)
              AND (cardinality(%s::text[]) = 0 OR metric_name = ANY(%s))
            ORDER BY recorded_at DESC
            LIMIT %s
        """
        rows = conn.execute(sql, (service, service, names, names, limit)).fetchall()
    out = []
    for r in rows:
        out.append(
            {
                "id": f"metric:{r['id']}",
                "source": "metrics",
                "tool": "get_metrics",
                "summary": (
                    f"{r['service']} {r['metric_name']}={r['value']}{r['unit'] or ''} "
                    f"at {r['recorded_at'].isoformat()}"
                ),
                "raw": {
                    "id": str(r["id"]),
                    "service": r["service"],
                    "metric_name": r["metric_name"],
                    "value": float(r["value"]),
                    "unit": r["unit"],
                    "recorded_at": r["recorded_at"].isoformat(),
                    "labels": r["labels"] or {},
                },
                "relevance": 0.7,
            }
        )
    return out


def get_recent_deployments(
    *,
    service: str | None = None,
    limit: int = 10,
    database_url: str | None = None,
) -> list[dict[str, Any]]:
    with get_conn(database_url) as conn:
        rows = conn.execute(
            """
            SELECT id, service, version, environment, status, deployed_at, change_summary, metadata
            FROM deployments
            WHERE (%s::text IS NULL OR service = %s)
            ORDER BY deployed_at DESC
            LIMIT %s
            """,
            (service, service, limit),
        ).fetchall()
    out = []
    for r in rows:
        out.append(
            {
                "id": f"deploy:{r['id']}",
                "source": "deployments",
                "tool": "get_recent_deployments",
                "summary": (
                    f"Deploy {r['service']} {r['version']} → {r['environment']} "
                    f"({r['status']}) at {r['deployed_at'].isoformat()}: {r['change_summary']}"
                ),
                "raw": {
                    "id": str(r["id"]),
                    "service": r["service"],
                    "version": r["version"],
                    "environment": r["environment"],
                    "status": r["status"],
                    "deployed_at": r["deployed_at"].isoformat(),
                    "change_summary": r["change_summary"],
                    "metadata": r["metadata"] or {},
                },
                "relevance": 0.75,
            }
        )
    return out


def get_service_dependencies(
    *,
    service: str,
    database_url: str | None = None,
) -> list[dict[str, Any]]:
    with get_conn(database_url) as conn:
        rows = conn.execute(
            """
            SELECT id, service, depends_on, dependency_type, criticality, notes
            FROM service_dependencies
            WHERE service = %s OR depends_on = %s
            ORDER BY criticality DESC, service
            """,
            (service, service),
        ).fetchall()
        # Also pull architecture docs
        arch = search_documents(
            query=f"{service} dependencies architecture",
            doc_types=["architecture"],
            limit=4,
            database_url=database_url,
        )
    out = []
    for r in rows:
        out.append(
            {
                "id": f"dep:{r['id']}",
                "source": "dependencies",
                "tool": "get_service_dependencies",
                "summary": (
                    f"{r['service']} → {r['depends_on']} "
                    f"({r['dependency_type']}, {r['criticality']}): {r['notes']}"
                ),
                "raw": dict(r) | {"id": str(r["id"])},
                "relevance": 0.8 if r["criticality"] == "critical" else 0.6,
            }
        )
    for row in arch:
        out.append(
            {
                "id": f"arch:{row['chunk_id']}",
                "source": "architecture",
                "tool": "get_service_dependencies",
                "summary": row["content"][:400],
                "raw": {
                    "document_id": str(row["document_id"]),
                    "title": row["title"],
                    "score": float(row["score"]),
                },
                "relevance": float(row["score"]),
            }
        )
    return out


def search_previous_incidents(
    *,
    query: str,
    service: str | None = None,
    limit: int = 8,
    database_url: str | None = None,
) -> list[dict[str, Any]]:
    semantic = search_documents(
        query=query,
        doc_types=["incident"],
        limit=limit,
        database_url=database_url,
    )
    out = []
    for row in semantic:
        if service and row.get("service") and row["service"] != service:
            # still allow high-score cross-service matches
            if float(row["score"]) < 0.35:
                continue
        out.append(
            {
                "id": f"incdoc:{row['chunk_id']}",
                "source": "incidents",
                "tool": "search_previous_incidents",
                "summary": row["content"][:450],
                "raw": {
                    "document_id": str(row["document_id"]),
                    "title": row["title"],
                    "service": row.get("service"),
                    "score": float(row["score"]),
                },
                "relevance": float(row["score"]),
            }
        )

    with get_conn(database_url) as conn:
        rows = conn.execute(
            """
            SELECT id, title, service, severity, root_cause, summary, resolved_at
            FROM past_incidents
            WHERE (%s::text IS NULL OR service = %s)
              AND (title ILIKE '%%' || %s || '%%' OR summary ILIKE '%%' || %s || '%%'
                   OR root_cause ILIKE '%%' || %s || '%%')
            ORDER BY resolved_at DESC NULLS LAST
            LIMIT %s
            """,
            (service, service, query[:40], query[:40], query[:40], limit),
        ).fetchall()
        for r in rows:
            eid = f"incident:{r['id']}"
            if any(x["id"] == eid for x in out):
                continue
            out.append(
                {
                    "id": eid,
                    "source": "incidents",
                    "tool": "search_previous_incidents",
                    "summary": (
                        f"[{r['severity']}] {r['title']} — root cause: {r['root_cause']}. "
                        f"{r['summary']}"
                    ),
                    "raw": {
                        "id": str(r["id"]),
                        "title": r["title"],
                        "service": r["service"],
                        "severity": r["severity"],
                        "root_cause": r["root_cause"],
                        "resolved_at": r["resolved_at"].isoformat() if r["resolved_at"] else None,
                    },
                    "relevance": 0.72,
                }
            )
    return out[:limit]


def search_runbooks(
    *,
    query: str,
    service: str | None = None,
    limit: int = 6,
    database_url: str | None = None,
) -> list[dict[str, Any]]:
    semantic = search_documents(
        query=query,
        doc_types=["runbook"],
        limit=limit,
        database_url=database_url,
    )
    out = []
    for row in semantic:
        if service and row.get("service") and row["service"] != service and float(row["score"]) < 0.3:
            continue
        out.append(
            {
                "id": f"runbook:{row['chunk_id']}",
                "source": "runbooks",
                "tool": "search_runbooks",
                "summary": row["content"][:450],
                "raw": {
                    "document_id": str(row["document_id"]),
                    "title": row["title"],
                    "service": row.get("service"),
                    "score": float(row["score"]),
                },
                "relevance": float(row["score"]),
            }
        )
    return out


TOOL_REGISTRY = {
    "search_logs": search_logs,
    "get_metrics": get_metrics,
    "get_recent_deployments": get_recent_deployments,
    "get_service_dependencies": get_service_dependencies,
    "search_previous_incidents": search_previous_incidents,
    "search_runbooks": search_runbooks,
}
