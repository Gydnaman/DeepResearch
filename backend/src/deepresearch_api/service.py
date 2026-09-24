from __future__ import annotations

import asyncio
import base64
import json
import logging
import re
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .graph import run_research_graph
from .limits import MAX_PERSISTED_EVENTS, MAX_RUNTIME_SECONDS
from .models import (
    Base,
    CitationRow,
    EvidenceRow,
    PlanRow,
    ReportRow,
    ResearchRunRow,
    RunEventRow,
    SearchTaskRow,
    SequenceCounter,
    now_utc,
)
from .providers import MockLLMProvider
from .rendering import MockReportRenderer
from .schemas import (
    TERMINAL_STATUSES,
    Citation,
    ErrorDetail,
    ErrorEnvelope,
    Evidence,
    OutputFormat,
    Plan,
    PlanStep,
    ProviderStatus,
    Report,
    ResearchEvent,
    ResearchRunCreate,
    ResearchRunCreated,
    ResearchRunSummary,
    RunList,
    RunStatus,
    SearchTask,
    StreamControlMessage,
    json_payload,
)

logger = logging.getLogger("deepresearch.runtime")
SSE_KEEPALIVE_SECONDS = 15.0


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def _summary(row: ResearchRunRow) -> ResearchRunSummary:
    return ResearchRunSummary(
        run_id=UUID(row.run_id),
        topic=row.topic,
        status=RunStatus(row.status),
        output_format=OutputFormat(row.output_format),
        sources=row.sources,
        created_at=_aware(row.created_at),
        updated_at=_aware(row.updated_at),
        warning=row.warning,
        failure_code=row.failure_code,
    )


async def _plan(run_id: UUID, req: ResearchRunCreate) -> Plan:
    questions = await MockLLMProvider().plan(req.topic, req.dimensions)
    steps = [
        PlanStep(id="intent", node="intent_router"),
        PlanStep(id="plan", node="planner"),
    ]
    for source in ("web", "local"):
        steps.append(
            PlanStep(
                id=f"scout-{source}",
                node=f"{source}_scout",
                source=source,
                status="planned" if getattr(req.sources, source) else "skipped",
            )
        )
    steps.extend(
        [
            PlanStep(id="review", node="evidence_judge"),
            PlanStep(id="analysis", node="analyst"),
            PlanStep(id="write", node="writer"),
            PlanStep(id="validate", node="citation_validator"),
        ]
    )
    return Plan(run_id=run_id, questions=questions, steps=steps, created_at=now_utc())


def _cursor_encode(data: dict) -> str:
    return (
        base64.urlsafe_b64encode(json.dumps(data, separators=(",", ":")).encode())
        .decode()
        .rstrip("=")
    )


def _cursor_decode(value: str) -> dict:
    try:
        decoded = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
        data = json.loads(decoded)
        if set(data) != {"snapshot", "created_at", "run_id"}:
            raise ValueError
        data["snapshot"] = int(data["snapshot"])
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        UUID(data["run_id"])
        if data["snapshot"] < 0:
            raise ValueError
        return data
    except (ValueError, TypeError, KeyError, json.JSONDecodeError):
        raise HTTPException(
            422, detail={"code": "validation_error", "message": "cursor is invalid"}
        ) from None


async def _persist_event(
    sessions: async_sessionmaker,
    run_id: str,
    *,
    event: str,
    phase: str,
    status: str,
    run_status: RunStatus,
    summary: str,
    node: str | None = None,
    task_id: UUID | None = None,
    evidence_ids: list[UUID] | None = None,
    error_code: str | None = None,
) -> ResearchEvent | None:
    async with sessions() as session, session.begin():
        row = await session.scalar(
            select(ResearchRunRow)
            .where(ResearchRunRow.run_id == run_id)
            .with_for_update()
        )
        if row is None or row.status in {s.value for s in TERMINAL_STATUSES}:
            return None
        if row.event_sequence >= MAX_PERSISTED_EVENTS - 1:
            return None
        row.event_sequence += 1
        row.updated_at = now_utc()
        item = ResearchEvent(
            id=row.event_sequence,
            run_id=UUID(run_id),
            event=event,
            phase=phase,
            node=node,
            status=status,
            run_status=run_status,
            summary=summary,
            task_id=task_id,
            evidence_ids=evidence_ids or [],
            error_code=error_code,
        )
        session.add(
            RunEventRow(run_id=run_id, sequence=item.id, payload=json_payload(item))
        )
        return item


async def _terminalize(
    sessions: async_sessionmaker,
    run_id: str,
    desired: RunStatus,
    *,
    report: Report | None = None,
    failure_code: str | None = None,
    warning: str | None = None,
    summary: str | None = None,
) -> ResearchRunSummary | None:
    async with sessions() as session, session.begin():
        row = await session.scalar(
            select(ResearchRunRow)
            .where(ResearchRunRow.run_id == run_id)
            .with_for_update()
        )
        if row is None:
            return None
        if row.status in {s.value for s in TERMINAL_STATUSES}:
            return _summary(row)
        final = (
            RunStatus.cancelled
            if row.cancel_requested and desired is RunStatus.completed
            else desired
        )
        row.status = final.value
        row.updated_at = now_utc()
        row.failure_code = failure_code if final is RunStatus.failed else None
        row.warning = warning if final is RunStatus.completed else None
        if final is RunStatus.completed and report:
            session.add(ReportRow(run_id=run_id, payload=json_payload(report)))
            for citation in report.citations:
                session.add(
                    CitationRow(
                        citation_id=str(citation.citation_id),
                        run_id=run_id,
                        evidence_id=str(citation.evidence_id),
                        section_id=citation.section_id,
                        marker=citation.marker,
                    )
                )
        row.event_sequence += 1
        event_name = {
            RunStatus.completed: "run.completed",
            RunStatus.failed: "run.failed",
            RunStatus.cancelled: "run.cancelled",
        }[final]
        event = ResearchEvent(
            id=row.event_sequence,
            run_id=UUID(run_id),
            event=event_name,
            phase="terminal",
            status=final.value,
            run_status=final,
            summary=summary or f"Research run {final.value}.",
            error_code=failure_code if final is RunStatus.failed else None,
        )
        session.add(
            RunEventRow(run_id=run_id, sequence=event.id, payload=json_payload(event))
        )
        return _summary(row)


async def _set_task(
    sessions: async_sessionmaker,
    task_id: str,
    status: str,
    *,
    evidence_ids: list[str] | None = None,
    error: str | None = None,
) -> SearchTask | None:
    async with sessions() as session, session.begin():
        row = await session.get(SearchTaskRow, task_id)
        if row is None:
            return None
        row.status = status
        if status == "running":
            row.started_at = now_utc()
        if status in {"completed", "failed", "cancelled"}:
            row.completed_at = now_utc()
        if evidence_ids is not None:
            row.evidence_ids = evidence_ids
        row.error = error
        return SearchTask.model_validate(
            {
                "task_id": row.task_id,
                "run_id": row.run_id,
                "source": row.source,
                "query_label": row.query_label,
                "status": row.status,
                "started_at": row.started_at,
                "completed_at": row.completed_at,
                "evidence_ids": row.evidence_ids,
                "error": row.error,
            }
        )


async def _close_active_tasks(
    sessions: async_sessionmaker, run_id: str, *, status: str, error: str
) -> None:
    async with sessions() as session:
        tasks = list(
            (
                await session.scalars(
                    select(SearchTaskRow).where(
                        SearchTaskRow.run_id == run_id,
                        SearchTaskRow.status.in_(["planned", "running"]),
                    )
                )
            ).all()
        )
    for task in tasks:
        await _set_task(sessions, task.task_id, status, error=error)


async def _build_report(
    sessions: async_sessionmaker,
    run_id: UUID,
    req: ResearchRunCreate,
    graph_result: dict,
    *,
    partial: bool,
) -> tuple[Report, list[Evidence], dict[str, list[str]]]:
    evidence_rows = graph_result.get("evidence", [])
    evidence_models: list[Evidence] = []
    for item in evidence_rows:
        evidence_models.append(
            Evidence(
                evidence_id=uuid4(),
                run_id=run_id,
                source_type=item["source_type"],
                source_label=item["source_label"],
                excerpt=item["excerpt"][:1000],
                relevance=item["relevance"],
                is_duplicate=False,
                fixture=True,
                published_at=item.get("published_at"),
            )
        )
    task_evidence_ids: dict[str, list[str]] = {}
    for item, evidence in zip(evidence_rows, evidence_models, strict=True):
        key = (
            "reflect"
            if item.get("call_stage") == "reflect"
            else f"scout:{evidence.source_type}"
        )
        task_evidence_ids.setdefault(key, []).append(str(evidence.evidence_id))
    citations: list[Citation] = []
    section_id = "findings"
    body = graph_result.get("report_body", "")
    if evidence_models:
        body = body.replace("[[cite:pending]]", "")
        for index, evidence in enumerate(evidence_models, start=1):
            citation = Citation(
                citation_id=uuid4(),
                run_id=run_id,
                evidence_id=evidence.evidence_id,
                section_id=section_id,
                marker=str(index),
            )
            citations.append(citation)
            body += f" [[cite:{citation.citation_id}]]"
    warning_parts = []
    if partial:
        warning_parts.append("partial_sources")
    if not evidence_models:
        warning_parts.append("no_evidence")
    report = MockReportRenderer().render(
        run_id, body, citations, warning=",".join(warning_parts) or None
    )
    async with sessions() as session, session.begin():
        session.add_all(
            [
                EvidenceRow(
                    evidence_id=str(evidence.evidence_id),
                    run_id=str(run_id),
                    source_type=evidence.source_type,
                    source_label=evidence.source_label,
                    excerpt=evidence.excerpt,
                    relevance=evidence.relevance,
                    is_duplicate=evidence.is_duplicate,
                    fixture=True,
                    published_at=evidence.published_at.isoformat()
                    if evidence.published_at
                    else None,
                    conflict_group_id=evidence.conflict_group_id,
                )
                for evidence in evidence_models
            ]
        )
    return report, evidence_models, task_evidence_ids


async def _worker(app: FastAPI, run_id: str) -> None:
    sessions = app.state.sessions
    cancel_before_start = False
    reflected_source: str | None = None
    reflected_task_id: UUID | None = None
    try:
        async with sessions() as session, session.begin():
            row = await session.scalar(
                select(ResearchRunRow)
                .where(ResearchRunRow.run_id == run_id)
                .with_for_update()
            )
            if row is None or row.status != RunStatus.queued.value:
                return
            if row.cancel_requested:
                cancel_before_start = True
            else:
                row.status = RunStatus.running.value
                row.updated_at = now_utc()
        if cancel_before_start:
            await _terminalize(
                sessions,
                run_id,
                RunStatus.cancelled,
                summary="Run cancelled before execution started.",
            )
            return
        async with sessions() as session:
            row = await session.get(ResearchRunRow, run_id)
            if row is None:
                return
            if row.status == RunStatus.cancelled.value:
                await _terminalize(
                    sessions,
                    run_id,
                    RunStatus.cancelled,
                    summary="Run cancelled before execution started.",
                )
                return
            await _persist_event(
                sessions,
                run_id,
                event="run.started",
                phase="startup",
                status="running",
                run_status=RunStatus.running,
                summary="Mock research runtime started.",
            )
            req = ResearchRunCreate.model_validate(
                {
                    "topic": row.topic,
                    "time_range": row.time_range,
                    "dimensions": row.dimensions,
                    "output_format": row.output_format,
                    "sources": row.sources,
                    "budgets": row.budgets,
                    "scenario": row.scenario,
                }
            )
        async with sessions() as session:
            tasks = list(
                (
                    await session.scalars(
                        select(SearchTaskRow).where(SearchTaskRow.run_id == run_id)
                    )
                ).all()
            )
        selected_sources = [
            source for source in ("web", "local") if getattr(req.sources, source)
        ][: req.budgets.max_scout_calls]
        for task in tasks:
            if task.status == "planned" and task.source in selected_sources:
                await _set_task(sessions, task.task_id, "running")
                await _persist_event(
                    sessions,
                    run_id,
                    event="search_task.started",
                    phase="scouting",
                    status="running",
                    run_status=RunStatus.running,
                    summary=f"{task.source.title()} fixture search started.",
                    task_id=UUID(task.task_id),
                )
        scenario = req.scenario.value if req.scenario else None

        async def on_node_event(event_name: str, node_name: str):
            phase_status = (
                "failed"
                if event_name == "node.failed"
                else "running"
                if event_name == "node.started"
                else "completed"
            )
            await _persist_event(
                sessions,
                run_id,
                event=event_name,
                phase=node_name,
                node=node_name,
                status=phase_status,
                run_status=RunStatus.running,
                summary=f"{node_name.replace('_', ' ').title()} {phase_status}.",
                error_code="runtime_failed" if event_name == "node.failed" else None,
            )

        async def on_reflect_started(source: str) -> None:
            nonlocal reflected_source, reflected_task_id
            if reflected_task_id is not None:
                return
            reflected_source = source
            reflected_task_id = uuid4()
            async with sessions() as session, session.begin():
                session.add(
                    SearchTaskRow(
                        task_id=str(reflected_task_id),
                        run_id=run_id,
                        source=source,
                        query_label=f"Reflect · {source.title()} follow-up",
                        status="running",
                        started_at=now_utc(),
                        evidence_ids=[],
                    )
                )
            await _persist_event(
                sessions,
                run_id,
                event="search_task.started",
                phase="reflect",
                status="running",
                run_status=RunStatus.running,
                summary=f"Reflect started a bounded {source} follow-up.",
                task_id=reflected_task_id,
            )

        async def execute_graph():
            if scenario == "cancel":
                await asyncio.sleep(0.4)
                raise asyncio.CancelledError()
            return await run_research_graph(
                topic=req.topic,
                sources=req.sources.model_dump(),
                dimensions=req.dimensions,
                scenario=scenario,
                output_format=req.output_format.value,
                max_reflect_rounds=req.budgets.max_reflect_rounds,
                max_scout_calls=req.budgets.max_scout_calls,
                max_concurrent_scouts=req.budgets.max_concurrent_scouts,
                time_range=(
                    req.time_range.model_dump(mode="json") if req.time_range else None
                ),
                on_node_event=on_node_event,
                on_reflect_started=on_reflect_started,
            )

        result = await asyncio.wait_for(
            execute_graph(),
            timeout=min(req.budgets.max_runtime_seconds, MAX_RUNTIME_SECONDS),
        )
        partial = bool(result.get("failed_sources"))
        async with sessions() as session:
            task_rows = list(
                (
                    await session.scalars(
                        select(SearchTaskRow).where(SearchTaskRow.run_id == run_id)
                    )
                ).all()
            )
        if partial and not result.get("evidence"):
            for task in task_rows:
                if task.source in result.get("failed_sources", []):
                    await _set_task(
                        sessions, task.task_id, "failed", error="source_unavailable"
                    )
                    await _persist_event(
                        sessions,
                        run_id,
                        event="search_task.failed",
                        phase="scouting",
                        status="failed",
                        run_status=RunStatus.running,
                        summary=f"{task.source.title()} fixture source failed.",
                        task_id=UUID(task.task_id),
                        error_code="source_unavailable",
                    )
                elif task.status in {"running", "planned"}:
                    await _set_task(
                        sessions, task.task_id, "skipped", error="scout_budget"
                    )
            await _terminalize(
                sessions,
                run_id,
                RunStatus.failed,
                failure_code="runtime_failed",
                summary="Every attempted Scout failed.",
            )
            return
        report, evidence_models, task_evidence_ids = await _build_report(
            sessions, UUID(run_id), req, result, partial=partial
        )
        if evidence_models:
            await _persist_event(
                sessions,
                run_id,
                event="evidence.added",
                phase="evidence_review",
                status="completed",
                run_status=RunStatus.running,
                summary=f"Added {len(evidence_models)} fixture evidence items.",
                evidence_ids=[e.evidence_id for e in evidence_models],
            )
        await _persist_event(
            sessions,
            run_id,
            event="budget.updated",
            phase="budget",
            status="running",
            run_status=RunStatus.running,
            summary=f"Scout calls used: {result.get('scout_calls_used', 0)} of {req.budgets.max_scout_calls}.",
        )
        for task in task_rows:
            if reflected_task_id and task.task_id == str(reflected_task_id):
                continue
            if task.status not in {"running", "planned"}:
                continue
            if task.source not in result.get("attempted_sources", []):
                if task.status in {"running", "planned"}:
                    await _set_task(
                        sessions, task.task_id, "skipped", error="scout_budget"
                    )
                continue
            failed = task.source in result.get("failed_sources", [])
            source_ids = task_evidence_ids.get(f"scout:{task.source}", [])
            await _set_task(
                sessions,
                task.task_id,
                "failed" if failed else "completed",
                evidence_ids=source_ids,
                error="source_unavailable" if failed else None,
            )
            await _persist_event(
                sessions,
                run_id,
                event="search_task.failed" if failed else "search_task.completed",
                phase="scouting",
                status="failed" if failed else "completed",
                run_status=RunStatus.running,
                summary=f"{task.source.title()} fixture source {'failed' if failed else 'completed'}.",
                task_id=UUID(task.task_id),
                evidence_ids=[UUID(value) for value in source_ids],
                error_code="source_unavailable" if failed else None,
            )
        if reflected_task_id:
            reflected_ids = task_evidence_ids.get("reflect", [])
            await _set_task(
                sessions,
                str(reflected_task_id),
                "completed",
                evidence_ids=reflected_ids,
            )
            await _persist_event(
                sessions,
                run_id,
                event="search_task.completed",
                phase="reflect",
                status="completed",
                run_status=RunStatus.running,
                summary="Reflect follow-up completed.",
                task_id=reflected_task_id,
                evidence_ids=[UUID(value) for value in reflected_ids],
            )
        warning = report.warning
        outcome = await _terminalize(
            sessions,
            run_id,
            RunStatus.completed,
            report=report,
            warning=warning,
            summary="Mock report is ready.",
        )
        if outcome and outcome.status is RunStatus.cancelled:
            return
    except asyncio.CancelledError:
        if app.state.shutting_down:
            return
        async with sessions() as session:
            task_rows = list(
                (
                    await session.scalars(
                        select(SearchTaskRow).where(
                            SearchTaskRow.run_id == run_id,
                            SearchTaskRow.status.in_(["planned", "running"]),
                        )
                    )
                ).all()
            )
        for task in task_rows:
            await _set_task(sessions, task.task_id, "cancelled")
        await _terminalize(
            sessions, run_id, RunStatus.cancelled, summary="Run cancelled by the user."
        )
    except TimeoutError:
        await _close_active_tasks(
            sessions, run_id, status="failed", error="budget_exhausted"
        )
        await _terminalize(
            sessions,
            run_id,
            RunStatus.failed,
            failure_code="budget_exhausted",
            summary="The configured runtime limit was reached.",
        )
    except Exception as error:  # Final runtime boundary; logs details privately and emits a safe terminal error.
        logger.exception("Research runtime failed for run %s", run_id)
        failure_code = (
            "citation_invalid_reference"
            if isinstance(error, ValueError) and "citation" in str(error).lower()
            else "runtime_failed"
        )
        await _close_active_tasks(sessions, run_id, status="failed", error=failure_code)
        await _terminalize(
            sessions,
            run_id,
            RunStatus.failed,
            failure_code=failure_code,
            summary="Mock runtime failed safely.",
        )
    finally:
        app.state.tasks.pop(run_id, None)


def create_app(
    database_url: str | None = None,
    *,
    scenarios_enabled: bool | None = None,
    initialize_schema: bool = True,
) -> FastAPI:
    import os

    url = database_url or os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://deepresearch:deepresearch@127.0.0.1:54329/deepresearch",
    )
    allow_scenarios = (
        scenarios_enabled
        if scenarios_enabled is not None
        else os.getenv("MOCK_SCENARIOS_ENABLED", "false").lower() == "true"
    )
    engine = create_async_engine(url, pool_pre_ping=True)
    sessions = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if initialize_schema:
            async with engine.begin() as connection:
                await connection.run_sync(Base.metadata.create_all)
        async with sessions() as session, session.begin():
            if await session.get(SequenceCounter, "runs") is None:
                session.add(SequenceCounter(name="runs", value=0))
            stranded = list(
                (
                    await session.scalars(
                        select(ResearchRunRow).where(
                            ResearchRunRow.status.in_(["queued", "running"])
                        )
                    )
                ).all()
            )
            for row in stranded:
                row.status = "failed"
                row.failure_code = "process_restarted"
                row.updated_at = now_utc()
                row.event_sequence += 1
                event = ResearchEvent(
                    id=row.event_sequence,
                    run_id=UUID(row.run_id),
                    event="run.failed",
                    phase="recovery",
                    status="failed",
                    run_status=RunStatus.failed,
                    summary="The API process restarted before this run completed.",
                    error_code="process_restarted",
                )
                session.add(
                    RunEventRow(
                        run_id=row.run_id,
                        sequence=event.id,
                        payload=json_payload(event),
                    )
                )
            stranded_ids = [row.run_id for row in stranded]
            if stranded_ids:
                active_tasks = list(
                    (
                        await session.scalars(
                            select(SearchTaskRow).where(
                                SearchTaskRow.run_id.in_(stranded_ids),
                                SearchTaskRow.status.in_(["planned", "running"]),
                            )
                        )
                    ).all()
                )
                for task in active_tasks:
                    task.status = "failed"
                    task.error = "process_restarted"
                    task.completed_at = now_utc()
        app.state.shutting_down = False
        yield
        app.state.shutting_down = True
        for task in list(app.state.tasks.values()):
            task.cancel()
        if app.state.tasks:
            await asyncio.gather(*app.state.tasks.values(), return_exceptions=True)
        await engine.dispose()

    app = FastAPI(title="DeepResearch Mock API", version="0.1.0", lifespan=lifespan)
    app.state.engine = engine
    app.state.sessions = sessions
    app.state.tasks = {}

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError):
        details = []
        for issue in exc.errors():
            location = (
                ".".join(str(part) for part in issue.get("loc", ()) if part != "body")
                or "request"
            )
            details.append(f"{location}: {issue.get('msg', 'invalid value')}")
        message = (
            "; ".join(dict.fromkeys(details[:3]))[:400]
            or "Request fields are invalid or outside the allowed bounds."
        )
        envelope = ErrorEnvelope(
            error=ErrorDetail(
                code="validation_error",
                message=message,
            )
        )
        return JSONResponse(status_code=422, content=json_payload(envelope))

    @app.exception_handler(HTTPException)
    async def http_error(_: Request, exc: HTTPException):
        detail = exc.detail if isinstance(exc.detail, dict) else {}
        code = str(
            detail.get("code")
            or {404: "not_found", 409: "conflict", 422: "validation_error"}.get(
                exc.status_code, "request_failed"
            )
        )
        message = str(detail.get("message") or "The request could not be completed.")
        retryable = bool(detail.get("retryable", code == "report_not_ready"))
        envelope = ErrorEnvelope(
            error=ErrorDetail(code=code, message=message, retryable=retryable)
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=json_payload(envelope),
            headers=exc.headers,
        )

    @app.get("/api/v1/health")
    async def health():
        return {"status": "ok", "mode": "mock", "fixture": True}

    @app.get("/api/v1/providers/status", response_model=list[ProviderStatus])
    async def provider_status():
        return [
            ProviderStatus(
                provider="Mock Web",
                kind="web_search",
                configured=True,
                message="Deterministic fixtures; no network requests.",
            ),
            ProviderStatus(
                provider="Mock Library",
                kind="knowledge",
                configured=True,
                message="Local fixture set; no external corpus configured.",
            ),
            ProviderStatus(
                provider="Mock Writer",
                kind="llm",
                configured=True,
                message="Template writer; no API key required.",
            ),
        ]

    @app.post(
        "/api/v1/research-runs", response_model=ResearchRunCreated, status_code=201
    )
    async def create_run(body: ResearchRunCreate):
        if body.scenario and not allow_scenarios:
            raise HTTPException(
                422,
                detail={
                    "code": "scenario_disabled",
                    "message": "Scenario selection is disabled by server configuration.",
                },
            )
        run_id = uuid4()
        plan = await _plan(run_id, body)
        async with sessions() as session, session.begin():
            counter = await session.scalar(
                select(SequenceCounter)
                .where(SequenceCounter.name == "runs")
                .with_for_update()
            )
            if counter is None:
                counter = SequenceCounter(name="runs", value=0)
                session.add(counter)
                await session.flush()
            counter.value += 1
            row = ResearchRunRow(
                run_id=str(run_id),
                topic=body.topic,
                status=RunStatus.planned.value,
                output_format=body.output_format.value,
                sources=body.sources.model_dump(mode="json"),
                budgets=body.budgets.model_dump(mode="json"),
                dimensions=body.dimensions,
                time_range=body.time_range.model_dump(mode="json")
                if body.time_range
                else None,
                scenario=body.scenario.value if body.scenario else None,
                created_at=now_utc(),
                updated_at=now_utc(),
                created_seq=counter.value,
                event_sequence=1,
            )
            session.add(row)
            session.add(PlanRow(run_id=str(run_id), payload=json_payload(plan)))
            for source in ("web", "local"):
                enabled = getattr(body.sources, source)
                task_id = uuid4()
                session.add(
                    SearchTaskRow(
                        task_id=str(task_id),
                        run_id=str(run_id),
                        source=source,
                        query_label=f"{source.title()} fixture query",
                        status="planned" if enabled else "skipped",
                        evidence_ids=[],
                    )
                )
                if not enabled:
                    row.event_sequence += 1
                    skipped = ResearchEvent(
                        id=row.event_sequence,
                        run_id=run_id,
                        event="node.skipped",
                        phase="planning",
                        node=f"{source}_scout",
                        status="skipped",
                        run_status=RunStatus.planned,
                        summary=f"{source.title()} Scout is disabled for this run.",
                    )
                    session.add(
                        RunEventRow(
                            run_id=str(run_id),
                            sequence=skipped.id,
                            payload=json_payload(skipped),
                        )
                    )
            event = ResearchEvent(
                id=1,
                run_id=run_id,
                event="plan.ready",
                phase="planning",
                node="planner",
                status="planned",
                run_status=RunStatus.planned,
                summary="A fixture-backed research plan is ready for review.",
            )
            session.add(
                RunEventRow(run_id=str(run_id), sequence=1, payload=json_payload(event))
            )
        return ResearchRunCreated(run=_summary(row), plan=plan)

    @app.get("/api/v1/research-runs", response_model=RunList)
    async def list_runs(limit: int = 20, cursor: str | None = None):
        if not 1 <= limit <= 50:
            raise HTTPException(
                422,
                detail={
                    "code": "validation_error",
                    "message": "limit must be between 1 and 50",
                },
            )
        async with sessions() as session:
            if cursor:
                decoded = _cursor_decode(cursor)
                snapshot = decoded["snapshot"]
                last_date = _aware(decoded["created_at"])
                last_id = decoded["run_id"]
            else:
                snapshot = int(
                    await session.scalar(
                        select(SequenceCounter.value).where(
                            SequenceCounter.name == "runs"
                        )
                    )
                    or 0
                )
                last_date = None
                last_id = None
            query = select(ResearchRunRow).where(ResearchRunRow.created_seq <= snapshot)
            if last_date is not None:
                query = query.where(
                    or_(
                        ResearchRunRow.created_at < last_date,
                        and_(
                            ResearchRunRow.created_at == last_date,
                            ResearchRunRow.run_id < last_id,
                        ),
                    )
                )
            rows = list(
                (
                    await session.scalars(
                        query.order_by(
                            ResearchRunRow.created_at.desc(),
                            ResearchRunRow.run_id.desc(),
                        ).limit(limit + 1)
                    )
                ).all()
            )
        more = len(rows) > limit
        rows = rows[:limit]
        next_cursor = None
        if more and rows:
            tail = rows[-1]
            next_cursor = _cursor_encode(
                {
                    "snapshot": snapshot,
                    "created_at": _aware(tail.created_at).isoformat(),
                    "run_id": tail.run_id,
                }
            )
        return RunList(items=[_summary(row) for row in rows], next_cursor=next_cursor)

    async def require_run(session: AsyncSession, run_id: UUID) -> ResearchRunRow:
        row = await session.get(ResearchRunRow, str(run_id))
        if row is None:
            raise HTTPException(
                404,
                detail={
                    "code": "run_not_found",
                    "message": "Research run was not found.",
                },
            )
        return row

    @app.get("/api/v1/research-runs/{run_id}", response_model=ResearchRunSummary)
    async def get_run(run_id: UUID):
        async with sessions() as session:
            return _summary(await require_run(session, run_id))

    @app.get("/api/v1/research-runs/{run_id}/plan", response_model=Plan)
    async def get_plan(run_id: UUID):
        async with sessions() as session:
            await require_run(session, run_id)
            plan_row = await session.get(PlanRow, str(run_id))
            return Plan.model_validate(plan_row.payload)

    @app.get(
        "/api/v1/research-runs/{run_id}/search-tasks", response_model=list[SearchTask]
    )
    async def get_search_tasks(run_id: UUID):
        async with sessions() as session:
            await require_run(session, run_id)
            rows = list(
                (
                    await session.scalars(
                        select(SearchTaskRow)
                        .where(SearchTaskRow.run_id == str(run_id))
                        .order_by(SearchTaskRow.source)
                    )
                ).all()
            )
            return [
                SearchTask.model_validate(
                    {
                        "task_id": r.task_id,
                        "run_id": r.run_id,
                        "source": r.source,
                        "query_label": r.query_label,
                        "status": r.status,
                        "started_at": r.started_at,
                        "completed_at": r.completed_at,
                        "evidence_ids": r.evidence_ids,
                        "error": r.error,
                    }
                )
                for r in rows
            ]

    @app.get("/api/v1/research-runs/{run_id}/evidence", response_model=list[Evidence])
    async def get_evidence(run_id: UUID):
        async with sessions() as session:
            await require_run(session, run_id)
            rows = list(
                (
                    await session.scalars(
                        select(EvidenceRow)
                        .where(EvidenceRow.run_id == str(run_id))
                        .order_by(EvidenceRow.relevance.desc())
                    )
                ).all()
            )
            return [
                Evidence.model_validate(
                    {
                        "evidence_id": r.evidence_id,
                        "run_id": r.run_id,
                        "source_type": r.source_type,
                        "source_label": r.source_label,
                        "excerpt": r.excerpt,
                        "relevance": r.relevance,
                        "is_duplicate": r.is_duplicate,
                        "fixture": r.fixture,
                        "published_at": r.published_at,
                        "conflict_group_id": r.conflict_group_id,
                    }
                )
                for r in rows
            ]

    @app.get("/api/v1/research-runs/{run_id}/report", response_model=Report)
    async def get_report(run_id: UUID):
        async with sessions() as session:
            row = await require_run(session, run_id)
            report = await session.get(ReportRow, str(run_id))
            if report:
                return Report.model_validate(report.payload)
            if row.status in {"failed", "cancelled"}:
                raise HTTPException(
                    409,
                    detail={
                        "code": "run_terminal",
                        "message": "This run ended without a report.",
                    },
                )
            raise HTTPException(
                409,
                detail={
                    "code": "report_not_ready",
                    "message": "The report is not ready yet.",
                },
            )

    @app.post("/api/v1/research-runs/{run_id}/start", response_model=ResearchRunSummary)
    async def start_run(run_id: UUID):
        key = str(run_id)
        should_start = False
        async with sessions() as session, session.begin():
            row = await session.scalar(
                select(ResearchRunRow)
                .where(ResearchRunRow.run_id == key)
                .with_for_update()
            )
            if row is None:
                raise HTTPException(
                    404,
                    detail={
                        "code": "run_not_found",
                        "message": "Research run was not found.",
                    },
                )
            if row.status == "planned":
                row.status = "queued"
                row.updated_at = now_utc()
                row.event_sequence += 1
                event = ResearchEvent(
                    id=row.event_sequence,
                    run_id=run_id,
                    event="run.queued",
                    phase="startup",
                    status="queued",
                    run_status=RunStatus.queued,
                    summary="Mock run queued.",
                )
                session.add(
                    RunEventRow(
                        run_id=key, sequence=event.id, payload=json_payload(event)
                    )
                )
                should_start = True
            elif row.status in {"queued", "running"}:
                pass
            else:
                raise HTTPException(
                    409,
                    detail={
                        "code": "run_terminal",
                        "message": "This run can no longer be started.",
                    },
                )
            result = _summary(row)
        if should_start and key not in app.state.tasks:
            app.state.tasks[key] = asyncio.create_task(
                _worker(app, key), name=f"deepresearch:{key}"
            )
        return result

    @app.post(
        "/api/v1/research-runs/{run_id}/cancel", response_model=ResearchRunSummary
    )
    async def cancel_run(run_id: UUID):
        key = str(run_id)
        cancel_task = None
        cancelled_from_plan = False
        async with sessions() as session, session.begin():
            row = await session.scalar(
                select(ResearchRunRow)
                .where(ResearchRunRow.run_id == key)
                .with_for_update()
            )
            if row is None:
                raise HTTPException(
                    404,
                    detail={
                        "code": "run_not_found",
                        "message": "Research run was not found.",
                    },
                )
            if row.status == RunStatus.planned.value:
                cancelled_from_plan = True
                row.status = RunStatus.cancelled.value
                row.updated_at = now_utc()
                row.event_sequence += 1
                event = ResearchEvent(
                    id=row.event_sequence,
                    run_id=run_id,
                    event="run.cancelled",
                    phase="terminal",
                    status="cancelled",
                    run_status=RunStatus.cancelled,
                    summary="Planned run cancelled.",
                )
                session.add(
                    RunEventRow(
                        run_id=key, sequence=event.id, payload=json_payload(event)
                    )
                )
            elif row.status in {"queued", "running"}:
                row.cancel_requested = True
                row.updated_at = now_utc()
                cancel_task = app.state.tasks.get(key)
            result = _summary(row)
        if cancelled_from_plan:
            async with sessions() as session:
                planned_tasks = list(
                    (
                        await session.scalars(
                            select(SearchTaskRow).where(
                                SearchTaskRow.run_id == key,
                                SearchTaskRow.status == "planned",
                            )
                        )
                    ).all()
                )
            for task in planned_tasks:
                await _set_task(sessions, task.task_id, "cancelled")
        if cancel_task and not cancel_task.done():
            cancel_task.cancel()
        elif result.status is RunStatus.queued:
            await _close_active_tasks(
                sessions, key, status="cancelled", error="cancelled"
            )
            await _terminalize(
                sessions,
                key,
                RunStatus.cancelled,
                summary="Queued run cancelled before execution started.",
            )
            async with sessions() as session:
                result = _summary(await session.get(ResearchRunRow, key))
        return result

    @app.get("/api/v1/research-runs/{run_id}/events")
    async def get_events(run_id: UUID, request: Request, after: str | None = None):
        key = str(run_id)
        async with sessions() as session:
            row = await session.get(ResearchRunRow, key)
            if row is None:
                raise HTTPException(
                    404,
                    detail={
                        "code": "run_not_found",
                        "message": "Research run was not found.",
                    },
                )
            upper = row.event_sequence
        header = request.headers.get("last-event-id")
        cursor_text = header if header is not None else after
        cursor = 0
        invalid = False
        if cursor_text is not None:
            if not re.fullmatch(r"\d+", cursor_text):
                invalid = True
            else:
                normalized_cursor = cursor_text.lstrip("0") or "0"
                upper_text = str(upper)
                invalid = len(normalized_cursor) > len(upper_text) or (
                    len(normalized_cursor) == len(upper_text)
                    and normalized_cursor > upper_text
                )
                if not invalid:
                    cursor = int(normalized_cursor)

        async def event_stream():
            nonlocal cursor
            loop = asyncio.get_running_loop()
            last_send = loop.time()
            if invalid:
                payload = json.dumps(
                    json_payload(
                        StreamControlMessage(
                            run_id=run_id,
                            code="invalid_event_cursor",
                            message="Event cursor must be a non-negative sequence already allocated for this run.",
                        )
                    ),
                    ensure_ascii=False,
                )
                yield f"event: stream.error\ndata: {payload}\n\n"
                return
            while True:
                now = loop.time()
                if now - last_send >= SSE_KEEPALIVE_SECONDS:
                    yield ": keep-alive\n\n"
                    last_send = now
                async with sessions() as session:
                    rows = list(
                        (
                            await session.scalars(
                                select(RunEventRow)
                                .where(
                                    RunEventRow.run_id == key,
                                    RunEventRow.sequence > cursor,
                                )
                                .order_by(RunEventRow.sequence)
                            )
                        ).all()
                    )
                    state = await session.get(ResearchRunRow, key)
                for row in rows:
                    cursor = row.sequence
                    yield f"id: {row.sequence}\nevent: {row.payload['event']}\ndata: {json.dumps(row.payload, ensure_ascii=False)}\n\n"
                    last_send = loop.time()
                if (
                    state.status in {s.value for s in TERMINAL_STATUSES}
                    and cursor >= state.event_sequence
                ):
                    return
                if await request.is_disconnected():
                    return
                await asyncio.sleep(0.25)

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    def openapi_with_sse_event_schema():
        if app.openapi_schema:
            return app.openapi_schema
        schema = get_openapi(title=app.title, version=app.version, routes=app.routes)
        components = schema.setdefault("components", {}).setdefault("schemas", {})
        api_schemas = {
            model.__name__: model.model_json_schema(
                ref_template="#/components/schemas/{model}"
            )
            for model in (ResearchEvent, StreamControlMessage, ErrorEnvelope)
        }
        for name, model_schema in api_schemas.items():
            for definition_name, definition in model_schema.pop("$defs", {}).items():
                components.setdefault(definition_name, definition)
            components[name] = model_schema

        event_response = {
            "oneOf": [
                {"$ref": "#/components/schemas/ResearchEvent"},
                {"$ref": "#/components/schemas/StreamControlMessage"},
            ]
        }
        schema["paths"]["/api/v1/research-runs/{run_id}/events"]["get"]["responses"][
            "200"
        ] = {
            "description": "Persisted events are sent as Server-Sent Events.",
            "content": {"text/event-stream": {"schema": event_response}},
        }
        error_content = {
            "application/json": {
                "schema": {"$ref": "#/components/schemas/ErrorEnvelope"}
            }
        }
        for path, path_item in schema["paths"].items():
            for operation in path_item.values():
                if not isinstance(operation, dict) or "responses" not in operation:
                    continue
                responses = operation["responses"]
                if "422" in responses:
                    responses["422"] = {
                        "description": "Request validation failed.",
                        "content": error_content,
                    }
                if "{run_id}" in path:
                    responses["404"] = {
                        "description": "The research run was not found.",
                        "content": error_content,
                    }
            if "{run_id}" in path:
                for method, description in (
                    ("get", "The report is not ready yet."),
                    ("post", "The run can no longer be started."),
                ):
                    response_path = (
                        path.endswith("/report")
                        if method == "get"
                        else path.endswith("/start")
                    )
                    if response_path and method in path_item:
                        path_item[method]["responses"]["409"] = {
                            "description": description,
                            "content": error_content,
                        }
        app.openapi_schema = schema
        return app.openapi_schema

    app.openapi = openapi_with_sse_event_schema
    return app
