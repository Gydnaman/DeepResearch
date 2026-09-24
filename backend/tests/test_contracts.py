from uuid import uuid4

import pytest
from pydantic import ValidationError

from deepresearch_api.limits import MAX_PERSISTED_EVENTS
from deepresearch_api.schemas import (
    Citation,
    Evidence,
    OutputFormat,
    Report,
    ReportSection,
    ResearchRunCreate,
    RunBudgets,
)


def base_request(**overrides):
    payload = {
        "topic": "  renewable energy storage  ",
        "sources": {"web": True, "local": True},
        "output_format": "narrative",
        "dimensions": ["cost", "reliability"],
        "time_range": {"start": "2025-01-01", "end": "2025-12-31"},
    }
    payload.update(overrides)
    return payload


def test_run_create_normalizes_topic_and_accepts_valid_contract():
    request = ResearchRunCreate.model_validate(base_request())

    assert request.topic == "renewable energy storage"
    assert request.sources.web is True
    assert request.output_format is OutputFormat.narrative


@pytest.mark.parametrize(
    "topic",
    ["", "   ", "x" * 501],
)
def test_run_create_rejects_empty_or_oversized_topic(topic):
    with pytest.raises(ValidationError):
        ResearchRunCreate.model_validate(base_request(topic=topic))


def test_run_create_rejects_invalid_ranges_sources_formats_and_dimensions():
    bad_requests = [
        base_request(time_range={"start": "2025-12-31", "end": "2025-01-01"}),
        base_request(sources={"web": False, "local": False}),
        base_request(output_format="slides"),
        base_request(dimensions=["x"] * 13),
        base_request(dimensions=[""]),
        base_request(time_range={"start": "2025-01-01"}),
    ]

    for payload in bad_requests:
        with pytest.raises(ValidationError):
            ResearchRunCreate.model_validate(payload)


def test_budgets_may_only_use_approved_bounds():
    assert RunBudgets().max_reflect_rounds == 1
    assert MAX_PERSISTED_EVENTS == 100

    for budgets in (
        {"max_reflect_rounds": 2},
        {"max_scout_calls": 4},
        {"max_concurrent_scouts": 3},
        {"max_runtime_seconds": 121},
        {"max_reflect_rounds": -1},
        {"max_tokens": 100_001},
    ):
        with pytest.raises(ValidationError):
            ResearchRunCreate.model_validate(base_request(budgets=budgets))


def test_evidence_excerpt_is_bounded():
    with pytest.raises(ValidationError):
        Evidence(
            run_id=uuid4(),
            source_type="web",
            source_label="Fixture",
            excerpt="x" * 1001,
            relevance=0.5,
            is_duplicate=False,
            fixture=True,
        )


def test_report_citations_must_match_markers_and_run():
    run_id = uuid4()
    evidence_id = uuid4()
    citation_id = uuid4()
    citation = Citation(
        citation_id=citation_id,
        run_id=run_id,
        evidence_id=evidence_id,
        section_id="findings",
        marker="1",
    )
    section = ReportSection(
        section_id="findings",
        title="Findings",
        body=f"Evidence supports this claim [[cite:{citation_id}]].",
        citation_ids=[citation_id],
    )

    report = Report(
        run_id=run_id,
        sections=[section],
        citations=[citation],
        fixture=True,
        mode="mock",
    )

    assert report.sections[0].citation_ids == [citation_id]


def test_report_rejects_orphan_or_cross_run_citation():
    run_id = uuid4()
    wrong_run_id = uuid4()
    citation_id = uuid4()

    with pytest.raises(ValidationError):
        Report(
            run_id=run_id,
            sections=[
                ReportSection(
                    section_id="summary",
                    title="Summary",
                    body="No reference.",
                    citation_ids=[citation_id],
                )
            ],
            citations=[
                Citation(
                    citation_id=citation_id,
                    run_id=wrong_run_id,
                    evidence_id=uuid4(),
                    section_id="summary",
                    marker="1",
                )
            ],
            fixture=True,
            mode="mock",
        )


def test_date_fields_are_iso_dates():
    with pytest.raises(ValidationError):
        ResearchRunCreate.model_validate(
            base_request(time_range={"start": "yesterday", "end": "2025-12-31"})
        )
