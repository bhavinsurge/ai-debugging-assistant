from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.core.config import get_settings
from app.db.session import get_conn
from app.llm.mock_llm import sanitize_hypothesis_evidence_ids
from app.llm.provider import get_llm
from app.models.schemas import (
    EvidenceItem,
    Hypothesis,
    InvestigationReport,
    InvestigationStep,
    InvestigationSummary,
)
from app.tools import (
    get_metrics,
    get_recent_deployments,
    get_service_dependencies,
    search_logs,
    search_previous_incidents,
    search_runbooks,
)

try:
    import redis as redis_lib
except Exception:  # pragma: no cover
    redis_lib = None


def _redis():
    settings = get_settings()
    if redis_lib is None:
        return None
    try:
        client = redis_lib.from_url(settings.redis_url, decode_responses=True)
        client.ping()
        return client
    except Exception:
        return None


def collect_evidence(
    *,
    symptom: str,
    service: str | None,
    database_url: str | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    settings = get_settings()
    r = _redis()
    tools_invoked: list[str] = []
    evidence: list[dict[str, Any]] = []

    def add(tool_name: str, items: list[dict[str, Any]]) -> None:
        tools_invoked.append(tool_name)
        evidence.extend(items)

    add(
        "search_logs",
        search_logs(
            query=symptom,
            service=service,
            limit=10,
            database_url=database_url,
            redis_client=r,
            cache_ttl=settings.cache_ttl_seconds,
        ),
    )
    add(
        "get_metrics",
        get_metrics(service=service, limit=15, database_url=database_url),
    )
    add(
        "get_recent_deployments",
        get_recent_deployments(service=service, limit=8, database_url=database_url),
    )
    if service:
        add(
            "get_service_dependencies",
            get_service_dependencies(service=service, database_url=database_url),
        )
    add(
        "search_previous_incidents",
        search_previous_incidents(
            query=symptom, service=service, limit=6, database_url=database_url
        ),
    )
    add(
        "search_runbooks",
        search_runbooks(query=symptom, service=service, limit=5, database_url=database_url),
    )

    # Deduplicate by id keeping highest relevance
    best: dict[str, dict[str, Any]] = {}
    for item in evidence:
        eid = str(item["id"])
        prev = best.get(eid)
        if prev is None or float(item.get("relevance") or 0) > float(prev.get("relevance") or 0):
            best[eid] = item
    merged = list(best.values())
    merged.sort(key=lambda x: float(x.get("relevance") or 0), reverse=True)
    return merged[:40], tools_invoked


def run_investigation(
    *,
    investigation_id: UUID,
    title: str,
    symptom: str,
    service: str | None,
    environment: str,
    database_url: str | None = None,
    llm_provider: str | None = None,
) -> InvestigationReport:
    settings = get_settings()
    with get_conn(database_url) as conn:
        conn.execute(
            "UPDATE investigations SET status = 'running', updated_at = NOW() WHERE id = %s",
            (str(investigation_id),),
        )
        conn.commit()

    evidence_raw, tools_invoked = collect_evidence(
        symptom=symptom, service=service, database_url=database_url
    )
    llm = get_llm(llm_provider)
    analysis = llm.analyze(
        symptom=symptom,
        service=service,
        environment=environment,
        evidence=evidence_raw,
        tools_invoked=tools_invoked,
    )
    allowed = {str(e["id"]) for e in evidence_raw}
    analysis = sanitize_hypothesis_evidence_ids(analysis, allowed)

    evidence_items = [EvidenceItem(**e) for e in evidence_raw]
    primary = analysis.get("primary_hypothesis")
    primary_h = Hypothesis(**primary) if primary else None
    alternates = [Hypothesis(**h) for h in analysis.get("alternate_hypotheses") or []]
    steps = [InvestigationStep(**s) for s in analysis.get("recommended_investigation") or []]
    warnings = list(analysis.get("warnings") or [])
    completed_at = datetime.now(timezone.utc)

    report_payload = {
        "tools_invoked": tools_invoked,
        "evidence": [e.model_dump(mode="json") for e in evidence_items],
        "primary_hypothesis": primary_h.model_dump(mode="json") if primary_h else None,
        "alternate_hypotheses": [h.model_dump(mode="json") for h in alternates],
        "recommended_investigation": [s.model_dump(mode="json") for s in steps],
        "warnings": warnings,
        "llm_provider": llm.name,
    }

    with get_conn(database_url) as conn:
        conn.execute(
            """
            UPDATE investigations
            SET status = 'completed',
                confidence = %s,
                report = %s::jsonb,
                tools_invoked = %s::jsonb,
                llm_provider = %s,
                completed_at = %s,
                updated_at = NOW()
            WHERE id = %s
            """,
            (
                primary_h.confidence if primary_h else None,
                json.dumps(report_payload),
                json.dumps(tools_invoked),
                llm.name,
                completed_at,
                str(investigation_id),
            ),
        )
        row = conn.execute(
            "SELECT created_at FROM investigations WHERE id = %s",
            (str(investigation_id),),
        ).fetchone()
        conn.commit()

    return InvestigationReport(
        investigation_id=investigation_id,
        title=title,
        symptom=symptom,
        service=service,
        environment=environment,
        status="completed",
        llm_provider=llm.name,
        tools_invoked=tools_invoked,
        evidence=evidence_items,
        primary_hypothesis=primary_h,
        alternate_hypotheses=alternates,
        recommended_investigation=steps,
        warnings=warnings,
        created_at=row["created_at"],
        completed_at=completed_at,
    )


def create_investigation_row(
    *,
    user_id: UUID,
    title: str,
    symptom: str,
    service: str | None,
    environment: str,
    time_window_minutes: int,
    database_url: str | None = None,
) -> dict[str, Any]:
    with get_conn(database_url) as conn:
        row = conn.execute(
            """
            INSERT INTO investigations (
                user_id, title, symptom, service, environment, time_window_minutes, status
            ) VALUES (%s, %s, %s, %s, %s, %s, 'queued')
            RETURNING id, title, symptom, service, environment, status, created_at
            """,
            (
                str(user_id),
                title,
                symptom,
                service,
                environment,
                time_window_minutes,
            ),
        ).fetchone()
        conn.commit()
    return dict(row)


def get_investigation(investigation_id: UUID, database_url: str | None = None) -> InvestigationReport | None:
    with get_conn(database_url) as conn:
        row = conn.execute(
            "SELECT * FROM investigations WHERE id = %s",
            (str(investigation_id),),
        ).fetchone()
    if not row:
        return None
    report = row.get("report") or {}
    if isinstance(report, str):
        report = json.loads(report)
    evidence = [EvidenceItem(**e) for e in report.get("evidence") or []]
    primary = report.get("primary_hypothesis")
    return InvestigationReport(
        investigation_id=row["id"],
        title=row["title"],
        symptom=row["symptom"],
        service=row["service"],
        environment=row["environment"],
        status=row["status"],
        llm_provider=row.get("llm_provider") or report.get("llm_provider") or "mock",
        tools_invoked=report.get("tools_invoked") or row.get("tools_invoked") or [],
        evidence=evidence,
        primary_hypothesis=Hypothesis(**primary) if primary else None,
        alternate_hypotheses=[Hypothesis(**h) for h in report.get("alternate_hypotheses") or []],
        recommended_investigation=[
            InvestigationStep(**s) for s in report.get("recommended_investigation") or []
        ],
        warnings=report.get("warnings") or [],
        created_at=row["created_at"],
        completed_at=row.get("completed_at"),
    )


def list_investigations(
    *, limit: int = 50, database_url: str | None = None
) -> list[InvestigationSummary]:
    with get_conn(database_url) as conn:
        rows = conn.execute(
            """
            SELECT id, title, symptom, service, environment, status, confidence, created_at, completed_at
            FROM investigations
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (limit,),
        ).fetchall()
    return [InvestigationSummary(**dict(r)) for r in rows]
