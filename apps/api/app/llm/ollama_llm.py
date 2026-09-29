"""
Optional Ollama provider. Used when LLM_PROVIDER=ollama and a local model is available.

Falls back to MockLLM behavior if Ollama is unreachable so the API stays usable.
"""

from __future__ import annotations

import json
import re
from typing import Any

import httpx

from app.llm.mock_llm import MockLLM, sanitize_hypothesis_evidence_ids


class OllamaLLM:
    name = "ollama"

    def __init__(self, *, base_url: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._fallback = MockLLM()

    def analyze(
        self,
        *,
        symptom: str,
        service: str | None,
        environment: str,
        evidence: list[dict[str, Any]],
        tools_invoked: list[str],
    ) -> dict[str, Any]:
        allowed = {str(e["id"]) for e in evidence}
        prompt = self._build_prompt(symptom, service, environment, evidence, tools_invoked)
        try:
            with httpx.Client(timeout=60.0) as client:
                resp = client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "format": "json",
                    },
                )
                resp.raise_for_status()
                data = resp.json()
            parsed = json.loads(data.get("response") or "{}")
            if "primary_hypothesis" not in parsed:
                raise ValueError("missing primary_hypothesis")
            parsed["warnings"] = list(parsed.get("warnings") or []) + [
                f"Generated via Ollama model {self.model}"
            ]
            return sanitize_hypothesis_evidence_ids(parsed, allowed)
        except Exception as exc:
            fallback = self._fallback.analyze(
                symptom=symptom,
                service=service,
                environment=environment,
                evidence=evidence,
                tools_invoked=tools_invoked,
            )
            fallback["warnings"] = list(fallback.get("warnings") or []) + [
                f"Ollama unavailable ({exc}); used MockLLM fallback."
            ]
            return sanitize_hypothesis_evidence_ids(fallback, allowed)

    def _build_prompt(
        self,
        symptom: str,
        service: str | None,
        environment: str,
        evidence: list[dict[str, Any]],
        tools_invoked: list[str],
    ) -> str:
        evidence_json = json.dumps(
            [
                {
                    "id": e["id"],
                    "tool": e.get("tool"),
                    "summary": e.get("summary"),
                    "relevance": e.get("relevance"),
                }
                for e in evidence
            ],
            indent=2,
        )
        return f"""You are RootCause, an evidence-bound software debugging assistant.
You MUST NOT invent evidence. Only cite evidence IDs from the provided list.
Return JSON with keys: primary_hypothesis, alternate_hypotheses, recommended_investigation, warnings.
primary_hypothesis: {{statement, confidence (0-1), evidence_ids[], rationale}}
recommended_investigation: [{{order, action, reason, related_evidence_ids[]}}]

Symptom: {symptom}
Service: {service}
Environment: {environment}
Tools invoked: {", ".join(tools_invoked)}

Evidence:
{evidence_json}
"""
