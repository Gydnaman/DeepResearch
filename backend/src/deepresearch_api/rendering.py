from typing import Protocol
from uuid import UUID

from .schemas import Citation, Report, ReportSection


class ReportRenderer(Protocol):
    def render(
        self,
        run_id: UUID,
        body: str,
        citations: list[Citation],
        warning: str | None = None,
    ) -> Report: ...


class MockReportRenderer:
    def render(
        self,
        run_id: UUID,
        body: str,
        citations: list[Citation],
        warning: str | None = None,
    ) -> Report:
        return Report(
            run_id=run_id,
            sections=[
                ReportSection(
                    section_id="findings",
                    title="研究发现",
                    body=body,
                    citation_ids=[citation.citation_id for citation in citations],
                )
            ],
            citations=citations,
            fixture=True,
            mode="mock",
            warning=warning,
        )
