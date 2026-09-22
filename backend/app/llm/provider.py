from __future__ import annotations

from typing import Any, Protocol

from app.core.config import get_settings
from app.llm.mock_llm import MockLLM
from app.llm.ollama_llm import OllamaLLM


class LLMProvider(Protocol):
    name: str

    def analyze(
        self,
        *,
        symptom: str,
        service: str | None,
        environment: str,
        evidence: list[dict[str, Any]],
        tools_invoked: list[str],
    ) -> dict[str, Any]:
        ...


def get_llm(provider: str | None = None) -> LLMProvider:
    settings = get_settings()
    name = (provider or settings.llm_provider or "mock").lower().strip()
    if name == "ollama":
        return OllamaLLM(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
        )
    return MockLLM()
