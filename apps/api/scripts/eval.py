#!/usr/bin/env python3
"""Evaluation harness for RootCause investigations."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.config import get_settings
from app.db.session import get_conn
from app.services import investigation as inv_service


def load_cases() -> list[dict]:
    path = ROOT / "data" / "eval" / "incidents.json"
    return json.loads(path.read_text())


def score_case(case: dict, report) -> dict:
    hyp = report.primary_hypothesis
    statement = (hyp.statement if hyp else "").lower()
    rationale = (hyp.rationale if hyp else "").lower()
    text = f"{statement} {rationale}"
    confidence = float(hyp.confidence) if hyp else 0.0
    evidence_ids = set(hyp.evidence_ids if hyp else [])
    tools = set(report.tools_invoked)

    # Root-cause identification: fraction of expected keywords present
    expected_kw = [k.lower() for k in case.get("expected_root_cause_keywords") or []]
    if case.get("expect_low_confidence"):
        rca_score = 1.0 if confidence <= float(case.get("max_confidence", 0.55)) else 0.0
    elif not expected_kw:
        rca_score = 1.0
    else:
        hits = sum(1 for k in expected_kw if k.lower() in text)
        rca_score = hits / len(expected_kw)

    # Evidence retrieval: expected tools invoked + hypothesis cites real evidence
    expected_tools = set(case.get("expected_evidence_tools") or [])
    tool_recall = (
        len(expected_tools & tools) / len(expected_tools) if expected_tools else 1.0
    )
    cited_ok = True
    allowed = {e.id for e in report.evidence}
    if evidence_ids and not evidence_ids.issubset(allowed):
        cited_ok = False
    if not case.get("expect_low_confidence") and hyp and confidence >= case.get("min_confidence", 0.5):
        evidence_score = 0.7 * tool_recall + 0.3 * (1.0 if evidence_ids and cited_ok else 0.0)
    else:
        evidence_score = 0.7 * tool_recall + 0.3 * (1.0 if cited_ok else 0.0)

    # False diagnosis: forbidden cause phrases appear in high-confidence primary hyp
    false_hits = []
    for phrase in case.get("forbidden_false_causes") or []:
        if phrase.lower() in statement and confidence >= 0.6:
            false_hits.append(phrase)
    false_diagnosis_penalty = 1.0 if false_hits else 0.0
    false_diagnosis_score = 1.0 - false_diagnosis_penalty  # 1 = good (no false diagnosis)

    # Investigation quality: has ordered steps referencing evidence
    steps = report.recommended_investigation or []
    step_score = 0.0
    if steps:
        step_score += 0.5
        if any(s.related_evidence_ids for s in steps):
            step_score += 0.3
        if len(steps) >= 2:
            step_score += 0.2

    conf_ok = True
    if case.get("expect_low_confidence"):
        conf_ok = confidence <= float(case.get("max_confidence", 0.55))
    elif case.get("min_confidence") is not None and expected_kw:
        conf_ok = confidence >= float(case["min_confidence"])

    passed = (
        rca_score >= 0.6
        and evidence_score >= 0.5
        and false_diagnosis_score >= 1.0
        and step_score >= 0.5
        and conf_ok
        and cited_ok
    )

    return {
        "id": case["id"],
        "passed": passed,
        "scores": {
            "root_cause_identification": round(rca_score, 3),
            "evidence_retrieval": round(evidence_score, 3),
            "false_diagnosis_avoidance": round(false_diagnosis_score, 3),
            "investigation_quality": round(step_score, 3),
            "confidence": round(confidence, 3),
        },
        "hypothesis": hyp.statement if hyp else None,
        "false_hits": false_hits,
        "tools_invoked": report.tools_invoked,
        "evidence_cited": list(evidence_ids),
    }


def main() -> int:
    settings = get_settings()
    # Ensure demo user exists
    with get_conn() as conn:
        user = conn.execute(
            "SELECT id, email, role FROM users WHERE email = %s",
            ("admin@rootcause.local",),
        ).fetchone()
    if not user:
        print("No seed user found. Run scripts/seed.py first.", file=sys.stderr)
        return 2

    cases = load_cases()
    results = []
    for case in cases:
        row = inv_service.create_investigation_row(
            user_id=user["id"],
            title=case["title"],
            symptom=case["symptom"],
            service=case.get("service"),
            environment=case.get("environment", "production"),
            time_window_minutes=60,
        )
        report = inv_service.run_investigation(
            investigation_id=row["id"],
            title=case["title"],
            symptom=case["symptom"],
            service=case.get("service"),
            environment=case.get("environment", "production"),
            llm_provider=settings.llm_provider,
        )
        results.append(score_case(case, report))

    # Aggregate
    keys = [
        "root_cause_identification",
        "evidence_retrieval",
        "false_diagnosis_avoidance",
        "investigation_quality",
    ]
    aggregates = {
        k: round(sum(r["scores"][k] for r in results) / len(results), 3) for k in keys
    }
    passed = sum(1 for r in results if r["passed"])
    gate_pass = passed >= int(0.8 * len(results)) and aggregates["false_diagnosis_avoidance"] >= 0.8

    out = {
        "provider": settings.llm_provider,
        "cases": len(results),
        "passed": passed,
        "pass_rate": round(passed / len(results), 3),
        "aggregates": aggregates,
        "gate_pass": gate_pass,
        "results": results,
    }
    print(json.dumps(out, indent=2))
    out_path = ROOT / "data" / "eval" / "last_results.json"
    out_path.write_text(json.dumps(out, indent=2))
    return 0 if gate_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
