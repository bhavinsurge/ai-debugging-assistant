"""
Deterministic MockLLM for CI and environments without Ollama.

Rules:
- Never invent evidence IDs; every conclusion references retrieved evidence.
- Score signatures from symptom + evidence overlap; pick the best match.
- If evidence is insufficient, lower confidence and say so explicitly.
"""

from __future__ import annotations

from typing import Any


def _evidence_blob(evidence: list[dict[str, Any]]) -> str:
    parts = []
    for e in evidence:
        parts.append(f"{e.get('id', '')} {e.get('summary', '')} {e.get('raw', '')}")
    return " ".join(parts).lower()


def _ids_matching(evidence: list[dict[str, Any]], keywords: list[str]) -> list[str]:
    hits: list[str] = []
    for e in evidence:
        text = f"{e.get('summary', '')} {e.get('raw', '')}".lower()
        if any(k.lower() in text for k in keywords):
            hits.append(str(e["id"]))
    return hits


def _unique(ids: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for i in ids:
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out


def _keyword_hits(text: str, keywords: list[str]) -> int:
    return sum(1 for k in keywords if k.lower() in text)


SIGNATURES: list[dict[str, Any]] = [
    {
        "id": "bad_checkout_deploy",
        "symptom_keywords": ["nullpointer", "paymentclient", "v2.14", "checkout 500", "500 errors"],
        "evidence_keywords": ["nullpointer", "paymentclient", "v2.14.0", "checkout", "deploy"],
        "statement": (
            "Recent checkout-api deploy v2.14.0 introduced a NullPointerException "
            "in PaymentClient, causing elevated 5xx on checkout."
        ),
        "confidence": 0.91,
        "steps": [
            "Diff checkout-api v2.13.x → v2.14.0 focusing on PaymentClient",
            "Confirm error rate spike aligns with deploy timestamp",
            "Roll back to last known-good version if confirmed",
        ],
    },
    {
        "id": "db_pool_exhaustion",
        "symptom_keywords": ["connection pool", "too many connections", "pool exhausted", "hikari"],
        "evidence_keywords": ["pool", "connection", "hikari", "postgres", "timeout"],
        "statement": (
            "PostgreSQL connection pool exhaustion on the primary database is starving "
            "upstream services and producing timeouts."
        ),
        "confidence": 0.88,
        "steps": [
            "Inspect active connections and long-running queries on primary",
            "Check for connection leaks after recent code/config change",
            "Temporarily raise pool size only after confirming leak source",
        ],
    },
    {
        "id": "payments_dependency",
        "symptom_keywords": ["payment-gateway", "circuit breaker", "upstream 503", "dependency timeout"],
        "evidence_keywords": ["payment-gateway", "circuit", "503", "dependency", "timeout"],
        "statement": (
            "Critical dependency payment-gateway is returning 503s; circuit breakers opened "
            "and checkout/order flows are failing as a cascade."
        ),
        "confidence": 0.86,
        "steps": [
            "Verify payment-gateway health and on-call status",
            "Confirm circuit breaker open state in checkout-api metrics",
            "Enable graceful degradation / queued capture if runbook allows",
        ],
    },
    {
        "id": "redis_stampede",
        "symptom_keywords": ["redis", "cache stampede", "read timed out", "cache miss storm"],
        "evidence_keywords": ["redis", "cache", "stampede", "timeout", "miss"],
        "statement": (
            "Redis timeouts triggered a cache miss stampede that overloaded the origin "
            "and amplified latency across catalog reads."
        ),
        "confidence": 0.84,
        "steps": [
            "Check Redis latency and eviction metrics around the incident window",
            "Confirm stampede protection / singleflight is enabled",
            "Warm critical keys and raise Redis timeout cautiously",
        ],
    },
    {
        "id": "memory_leak_config",
        "symptom_keywords": ["outofmemory", "heap", "memory leak", "feature flag", "batch_size"],
        "evidence_keywords": ["memory", "heap", "oom", "batch_size", "feature"],
        "statement": (
            "A configuration / feature-flag change increased batch sizes and led to "
            "heap exhaustion (OOM) in the worker service."
        ),
        "confidence": 0.83,
        "steps": [
            "Correlate OOM timestamps with feature-flag / config deploy",
            "Inspect heap dump or GC metrics for retained objects",
            "Revert batch_size flag and restart affected workers",
        ],
    },
]


def score_signature(sig: dict[str, Any], symptom_l: str, blob: str) -> float:
    """Symptom keywords are required; evidence alone must not invent a root cause."""
    s_hits = _keyword_hits(symptom_l, sig["symptom_keywords"])
    e_hits = _keyword_hits(blob, sig["evidence_keywords"])
    if s_hits == 0:
        return 0.0
    return s_hits * 3.0 + e_hits * 1.0


class MockLLM:
    name = "mock"

    def analyze(
        self,
        *,
        symptom: str,
        service: str | None,
        environment: str,
        evidence: list[dict[str, Any]],
        tools_invoked: list[str],
    ) -> dict[str, Any]:
        blob = _evidence_blob(evidence)
        symptom_l = symptom.lower()
        warnings: list[str] = []
        evidence_ids = [str(e["id"]) for e in evidence]

        if not evidence:
            return {
                "primary_hypothesis": {
                    "statement": "Insufficient evidence to form a root-cause hypothesis.",
                    "confidence": 0.15,
                    "evidence_ids": [],
                    "rationale": (
                        "No tool returned usable evidence. Refuse to invent causes; "
                        "gather logs, metrics, and recent deployments first."
                    ),
                },
                "alternate_hypotheses": [],
                "recommended_investigation": [
                    {
                        "order": 1,
                        "action": "Re-run investigation with a narrower service and time window",
                        "reason": "Empty evidence set — tooling returned nothing for this query.",
                        "related_evidence_ids": [],
                    }
                ],
                "warnings": ["No evidence collected; hypothesis intentionally non-specific."],
            }

        scored = [(score_signature(sig, symptom_l, blob), sig) for sig in SIGNATURES]
        scored.sort(key=lambda x: x[0], reverse=True)
        best_score, matched = scored[0]

        if best_score < 2.0:
            top = sorted(evidence, key=lambda e: float(e.get("relevance") or 0), reverse=True)[:5]
            cite = [str(e["id"]) for e in top]
            warnings.append(
                "No high-confidence signature matched; hypothesis is provisional and evidence-bound only."
            )
            return {
                "primary_hypothesis": {
                    "statement": (
                        f"Symptoms in {service or 'unknown service'} ({environment}) correlate with "
                        f"the strongest retrieved signals, but a specific root cause is not confirmed."
                    ),
                    "confidence": 0.42,
                    "evidence_ids": cite,
                    "rationale": (
                        "MockLLM requires matching evidence patterns. Available evidence was cited "
                        "without inventing unseen failures."
                    ),
                },
                "alternate_hypotheses": [],
                "recommended_investigation": [
                    {
                        "order": 1,
                        "action": "Expand log search around the symptom keywords",
                        "reason": "Top evidence did not lock a known failure mode.",
                        "related_evidence_ids": cite[:3],
                    },
                    {
                        "order": 2,
                        "action": "Compare recent deployments against metric inflection points",
                        "reason": "Deploy/metric correlation is the next highest-yield check.",
                        "related_evidence_ids": [
                            i for i in cite if i.startswith("deploy:") or i.startswith("metric:")
                        ],
                    },
                ],
                "warnings": warnings,
            }

        cite = _unique(_ids_matching(evidence, matched["evidence_keywords"]))
        cite = [c for c in cite if c in evidence_ids]
        if not cite:
            cite = evidence_ids[:3]
            warnings.append(
                "Signature matched but keyword overlap with evidence was weak; confidence reduced."
            )
            matched = {**matched, "confidence": min(float(matched["confidence"]), 0.55)}

        alt = []
        if len(scored) > 1 and scored[1][0] >= 2.0:
            alt_sig = scored[1][1]
            soft_hits = [
                c
                for c in _unique(_ids_matching(evidence, alt_sig["evidence_keywords"]))
                if c in evidence_ids
            ]
            if soft_hits:
                alt.append(
                    {
                        "statement": alt_sig["statement"],
                        "confidence": min(0.45, float(alt_sig["confidence"]) * 0.4),
                        "evidence_ids": soft_hits[:4],
                        "rationale": "Weaker alternate supported by partial evidence overlap.",
                    }
                )

        steps = []
        for i, action in enumerate(matched["steps"], start=1):
            steps.append(
                {
                    "order": i,
                    "action": action,
                    "reason": "Derived from matched evidence signature and runbook/tool results.",
                    "related_evidence_ids": cite[:4],
                }
            )

        runbook_ids = [e["id"] for e in evidence if e.get("tool") == "search_runbooks"]
        if runbook_ids:
            steps.append(
                {
                    "order": len(steps) + 1,
                    "action": "Follow the highest-ranked runbook steps cited in evidence",
                    "reason": "Runbook retrieval returned actionable guidance.",
                    "related_evidence_ids": runbook_ids[:3],
                }
            )

        return {
            "primary_hypothesis": {
                "statement": matched["statement"],
                "confidence": float(matched["confidence"]),
                "evidence_ids": cite,
                "rationale": (
                    f"Matched controlled signature '{matched['id']}' using only retrieved evidence "
                    f"from tools: {', '.join(tools_invoked)}."
                ),
            },
            "alternate_hypotheses": alt,
            "recommended_investigation": steps,
            "warnings": warnings,
        }


def sanitize_hypothesis_evidence_ids(
    result: dict[str, Any], allowed_ids: set[str]
) -> dict[str, Any]:
    """Hard safety rail: strip any evidence IDs not present in the collected set."""

    def clean_hyp(h: dict[str, Any] | None) -> dict[str, Any] | None:
        if not h:
            return h
        ids = [i for i in h.get("evidence_ids", []) if i in allowed_ids]
        out = dict(h)
        out["evidence_ids"] = ids
        if not ids and float(out.get("confidence", 0)) > 0.3:
            out["confidence"] = min(float(out["confidence"]), 0.3)
            out["rationale"] = (
                out.get("rationale", "")
                + " [confidence reduced: no valid evidence IDs after sanitization]"
            ).strip()
        return out

    cleaned = dict(result)
    cleaned["primary_hypothesis"] = clean_hyp(result.get("primary_hypothesis"))
    cleaned["alternate_hypotheses"] = [
        clean_hyp(h) for h in result.get("alternate_hypotheses", []) if h
    ]
    steps = []
    for s in result.get("recommended_investigation", []):
        step = dict(s)
        step["related_evidence_ids"] = [
            i for i in s.get("related_evidence_ids", []) if i in allowed_ids
        ]
        steps.append(step)
    cleaned["recommended_investigation"] = steps
    return cleaned
