from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def now_utc() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class SequenceCounter(Base):
    __tablename__ = "sequence_counters"
    name: Mapped[str] = mapped_column(String(40), primary_key=True)
    value: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class ResearchRunRow(Base):
    __tablename__ = "research_runs"
    run_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    topic: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    output_format: Mapped[str] = mapped_column(String(32), nullable=False)
    sources: Mapped[dict] = mapped_column(JSON, nullable=False)
    budgets: Mapped[dict] = mapped_column(JSON, nullable=False)
    dimensions: Mapped[list] = mapped_column(JSON, nullable=False)
    time_range: Mapped[dict | None] = mapped_column(JSON)
    scenario: Mapped[str | None] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=now_utc, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=now_utc
    )
    created_seq: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    event_sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cancel_requested: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    warning: Mapped[str | None] = mapped_column(String(80))
    failure_code: Mapped[str | None] = mapped_column(String(80))


class PlanRow(Base):
    __tablename__ = "plans"
    run_id: Mapped[str] = mapped_column(
        ForeignKey("research_runs.run_id", ondelete="CASCADE"), primary_key=True
    )
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)


class SearchTaskRow(Base):
    __tablename__ = "search_tasks"
    task_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(
        ForeignKey("research_runs.run_id", ondelete="CASCADE"), index=True
    )
    source: Mapped[str] = mapped_column(String(16), nullable=False)
    query_label: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    evidence_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    error: Mapped[str | None] = mapped_column(String(80))


class EvidenceRow(Base):
    __tablename__ = "evidence"
    evidence_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(
        ForeignKey("research_runs.run_id", ondelete="CASCADE"), index=True
    )
    source_type: Mapped[str] = mapped_column(String(16), nullable=False)
    source_label: Mapped[str] = mapped_column(String(200), nullable=False)
    excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    relevance: Mapped[float] = mapped_column(Float, nullable=False)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    fixture: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    published_at: Mapped[str | None] = mapped_column(String(10))
    conflict_group_id: Mapped[str | None] = mapped_column(String(80))
    __table_args__ = (
        UniqueConstraint("run_id", "evidence_id", name="uq_evidence_run_id"),
    )


class CitationRow(Base):
    __tablename__ = "citations"
    citation_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    evidence_id: Mapped[str] = mapped_column(String(36), nullable=False)
    section_id: Mapped[str] = mapped_column(String(100), nullable=False)
    marker: Mapped[str] = mapped_column(String(16), nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(
            ["run_id", "evidence_id"],
            ["evidence.run_id", "evidence.evidence_id"],
            name="fk_citation_run_evidence",
        ),
    )


class ReportRow(Base):
    __tablename__ = "reports"
    run_id: Mapped[str] = mapped_column(
        ForeignKey("research_runs.run_id", ondelete="CASCADE"), primary_key=True
    )
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)


class RunEventRow(Base):
    __tablename__ = "run_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(
        ForeignKey("research_runs.run_id", ondelete="CASCADE"), index=True
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    __table_args__ = (
        UniqueConstraint("run_id", "sequence", name="uq_event_run_sequence"),
    )
