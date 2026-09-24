from __future__ import annotations

import re
from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class OutputFormat(StrEnum):
    narrative = "narrative"
    executive_summary = "executive_summary"
    bullet_points = "bullet_points"


class RunStatus(StrEnum):
    planned = "planned"
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


TERMINAL_STATUSES = {RunStatus.completed, RunStatus.failed, RunStatus.cancelled}


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TimeRange(StrictModel):
    start: date
    end: date

    @model_validator(mode="after")
    def ordered(self):
        if self.start > self.end:
            raise ValueError("start must be on or before end")
        return self


class ResearchSources(StrictModel):
    web: bool = True
    local: bool = True

    @model_validator(mode="after")
    def at_least_one(self):
        if not self.web and not self.local:
            raise ValueError("at least one research source must be enabled")
        return self


class RunBudgets(StrictModel):
    max_reflect_rounds: int = Field(default=1, ge=0, le=1)
    max_scout_calls: int = Field(default=3, ge=1, le=3)
    max_concurrent_scouts: int = Field(default=2, ge=1, le=2)
    max_runtime_seconds: int = Field(default=120, ge=1, le=120)
    max_tokens: int | None = Field(default=None, ge=1, le=100_000)


class Scenario(StrEnum):
    success = "success"
    no_results = "no_results"
    partial_scout_failure = "partial_scout_failure"
    writer_error = "writer_error"
    citation_validation_error = "citation_validation_error"
    cancel = "cancel"


class ResearchRunCreate(StrictModel):
    topic: str = Field(min_length=1, max_length=500)
    time_range: TimeRange | None = None
    dimensions: list[str] = Field(default_factory=list, max_length=12)
    output_format: OutputFormat = OutputFormat.narrative
    sources: ResearchSources = Field(default_factory=ResearchSources)
    budgets: RunBudgets = Field(default_factory=RunBudgets)
    scenario: Scenario | None = None

    @field_validator("topic")
    @classmethod
    def trim_topic(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("topic cannot be empty")
        return value

    @field_validator("dimensions")
    @classmethod
    def validate_dimensions(cls, values: list[str]) -> list[str]:
        cleaned = [value.strip() for value in values]
        if any(not value or len(value) > 100 for value in cleaned):
            raise ValueError("dimensions must contain 1 to 100 characters")
        return cleaned

    @model_validator(mode="after")
    def scenario_sources(self):
        if self.scenario is Scenario.partial_scout_failure and not (
            self.sources.web and self.sources.local
        ):
            raise ValueError("partial_scout_failure requires web and local sources")
        return self


class ResearchRunSummary(StrictModel):
    run_id: UUID
    topic: str
    status: RunStatus
    output_format: OutputFormat
    sources: ResearchSources
    created_at: datetime
    updated_at: datetime
    mode: str = "mock"
    fixture: bool = True
    warning: str | None = None
    failure_code: str | None = None
    tokens_used: int | None = None


class PlanStep(StrictModel):
    id: str
    node: str
    source: str | None = None
    status: str = "planned"


class Plan(StrictModel):
    run_id: UUID
    questions: list[str]
    steps: list[PlanStep]
    created_at: datetime
    mode: str = "mock"
    fixture: bool = True


class SearchTask(StrictModel):
    task_id: UUID
    run_id: UUID
    source: str
    query_label: str
    status: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    evidence_ids: list[UUID] = Field(default_factory=list)
    error: str | None = None


class Evidence(StrictModel):
    evidence_id: UUID
    run_id: UUID
    source_type: str
    source_label: str
    excerpt: str = Field(max_length=1000)
    relevance: float = Field(ge=0, le=1)
    is_duplicate: bool = False
    fixture: bool = True
    published_at: date | None = None
    conflict_group_id: str | None = None


class Citation(StrictModel):
    citation_id: UUID
    run_id: UUID
    evidence_id: UUID
    section_id: str
    marker: str


class ReportSection(StrictModel):
    section_id: str
    title: str
    body: str
    citation_ids: list[UUID] = Field(default_factory=list)


class Report(StrictModel):
    run_id: UUID
    sections: list[ReportSection]
    citations: list[Citation] = Field(default_factory=list)
    fixture: bool = True
    mode: str = "mock"
    warning: str | None = None

    @model_validator(mode="after")
    def validate_citations(self):
        by_id = {citation.citation_id: citation for citation in self.citations}
        if len(by_id) != len(self.citations):
            raise ValueError("citation IDs must be unique")
        for citation in self.citations:
            if citation.run_id != self.run_id:
                raise ValueError("citation must belong to the report run")
        for section in self.sections:
            if any(cid not in by_id for cid in section.citation_ids):
                raise ValueError("section references an unknown citation")
            markers = set(re.findall(r"\[\[cite:([0-9a-fA-F-]{36})\]\]", section.body))
            expected = {str(cid) for cid in section.citation_ids}
            if markers != expected:
                raise ValueError("citation markers must match citation_ids")
            if any(
                by_id[cid].section_id != section.section_id
                for cid in section.citation_ids
            ):
                raise ValueError("citation section_id must match its report section")
        return self


class ResearchEvent(StrictModel):
    id: int
    run_id: UUID
    event: str
    phase: str
    node: str | None = None
    status: str
    run_status: RunStatus
    summary: str
    fixture: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    task_id: UUID | None = None
    evidence_ids: list[UUID] = Field(default_factory=list)
    error_code: str | None = None
    retryable: bool = False


class StreamControlMessage(StrictModel):
    run_id: UUID
    code: str
    message: str
    recovery: str = "restart_from_zero"


class ProviderStatus(StrictModel):
    provider: str
    kind: str
    configured: bool
    mode: str = "mock"
    fixture: bool = True
    message: str


class RunList(StrictModel):
    items: list[ResearchRunSummary]
    next_cursor: str | None = None


class ResearchRunCreated(StrictModel):
    run: ResearchRunSummary
    plan: Plan


class ErrorDetail(StrictModel):
    code: str
    message: str
    retryable: bool = False


class ErrorEnvelope(StrictModel):
    error: ErrorDetail


def json_payload(model: BaseModel) -> dict[str, Any]:
    return model.model_dump(mode="json")
