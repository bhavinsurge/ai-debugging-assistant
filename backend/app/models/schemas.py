from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ApiError(BaseModel):
    code: str
    message: str
    details: Any = None


class ApiResponse(BaseModel):
    success: bool = True
    data: Any = None
    error: ApiError | None = None


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8)


class UserOut(BaseModel):
    id: UUID
    email: str
    full_name: str
    role: str


class InvestigationCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    symptom: str = Field(min_length=10, max_length=4000)
    service: str | None = Field(default=None, max_length=120)
    environment: str = Field(default="production", max_length=40)
    time_window_minutes: int = Field(default=60, ge=5, le=1440)


class EvidenceItem(BaseModel):
    id: str
    source: str
    tool: str
    summary: str
    raw: dict[str, Any] = Field(default_factory=dict)
    relevance: float | None = None


class Hypothesis(BaseModel):
    statement: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_ids: list[str]
    rationale: str


class InvestigationStep(BaseModel):
    order: int
    action: str
    reason: str
    related_evidence_ids: list[str] = Field(default_factory=list)


class InvestigationReport(BaseModel):
    investigation_id: UUID
    title: str
    symptom: str
    service: str | None
    environment: str
    status: Literal["queued", "running", "completed", "failed"]
    llm_provider: str
    tools_invoked: list[str]
    evidence: list[EvidenceItem]
    primary_hypothesis: Hypothesis | None
    alternate_hypotheses: list[Hypothesis] = Field(default_factory=list)
    recommended_investigation: list[InvestigationStep] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    created_at: datetime
    completed_at: datetime | None = None


class InvestigationSummary(BaseModel):
    id: UUID
    title: str
    symptom: str
    service: str | None
    environment: str
    status: str
    confidence: float | None
    created_at: datetime
    completed_at: datetime | None
