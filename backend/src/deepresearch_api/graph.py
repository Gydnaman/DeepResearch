from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import date
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from .providers import MockKnowledgeProvider, MockLLMProvider, MockWebSearchProvider


class ResearchState(TypedDict, total=False):
    topic: str
    output_format: str
    sources: dict[str, bool]
    scenario: str
    dimensions: list[str]
    max_reflect_rounds: int
    max_scout_calls: int
    max_concurrent_scouts: int
    time_range: dict[str, str] | None
    scout_calls_used: int
    reflect_round: int
    needs_reflection: bool
    evidence: list[dict]
    failed_sources: list[str]
    summary: str
    report_body: str
    node_trace: list[str]
    reflect_target: str | None
    attempted_sources: list[str]
    reflect_history: list[str]


async def run_research_graph(
    *,
    topic: str,
    sources: dict,
    dimensions: list[str],
    scenario: str | None,
    output_format: str = "narrative",
    max_reflect_rounds: int,
    max_scout_calls: int = 3,
    max_concurrent_scouts: int = 2,
    time_range: dict[str, str] | None = None,
    on_node_event: Callable[[str, str], Awaitable[None]] | None = None,
    on_reflect_started: Callable[[str], Awaitable[None]] | None = None,
):
    web = MockWebSearchProvider()
    local = MockKnowledgeProvider()
    writer_provider = MockLLMProvider()

    async def router(state: ResearchState):
        return {"node_trace": ["intent_router"]}

    async def planner(state: ResearchState):
        return {"node_trace": state.get("node_trace", []) + ["planner"]}

    async def scouts(state: ResearchState):
        calls = []
        active = [name for name, enabled in state["sources"].items() if enabled]
        if state.get("reflect_target"):
            active = [state["reflect_target"]]
        remaining = max(
            0, state.get("max_scout_calls", 3) - state.get("scout_calls_used", 0)
        )
        active = active[:remaining]
        for name in active:
            if scenario == "partial_scout_failure" and name == "web":
                continue
            if scenario == "no_results":
                continue
            provider = web if name == "web" else local
            calls.append((name, provider.search(state["topic"])))
        semaphore = asyncio.Semaphore(state.get("max_concurrent_scouts", 2))

        async def bounded(call):
            async with semaphore:
                return await call

        results = await asyncio.gather(*(bounded(call) for _, call in calls))
        evidence = []
        for (name, _), rows in zip(calls, results, strict=True):
            if state.get("time_range"):
                start = date.fromisoformat(state["time_range"]["start"])
                end = date.fromisoformat(state["time_range"]["end"])
                rows = [
                    row
                    for row in rows
                    if row.get("published_at")
                    and start <= date.fromisoformat(row["published_at"]) <= end
                ]
            evidence.extend(
                {
                    **row,
                    "source_type": name,
                    "call_stage": "reflect" if state.get("reflect_target") else "scout",
                }
                for row in rows[:5]
            )
        failures = (
            ["web"]
            if scenario == "partial_scout_failure" and state["sources"].get("web")
            else []
        )
        return {
            "evidence": state.get("evidence", []) + evidence,
            "failed_sources": list(
                dict.fromkeys(state.get("failed_sources", []) + failures)
            ),
            "scout_calls_used": state.get("scout_calls_used", 0)
            + len(calls)
            + len(failures),
            "attempted_sources": list(
                dict.fromkeys(
                    state.get("attempted_sources", [])
                    + [name for name, _ in calls]
                    + failures
                )
            ),
            "reflect_target": None,
            "node_trace": state.get("node_trace", []) + ["scouts"],
        }

    async def evidence_judge(state: ResearchState):
        unique = []
        seen = set()
        for item in state.get("evidence", []):
            key = item["excerpt"]
            if key not in seen:
                unique.append(item)
                seen.add(key)
        return {
            "evidence": unique,
            "node_trace": state.get("node_trace", []) + ["evidence_judge"],
        }

    async def analyst(state: ResearchState):
        gap = (
            bool(state.get("evidence"))
            and "coverage" in state.get("dimensions", [])
            and state.get("reflect_round", 0) == 0
        )
        return {
            "needs_reflection": gap,
            "node_trace": state.get("node_trace", []) + ["analyst"],
        }

    async def reflect(state: ResearchState):
        available = [name for name, enabled in state["sources"].items() if enabled]
        target = available[-1] if available else None
        if target and on_reflect_started:
            await on_reflect_started(target)
        return {
            "reflect_round": state.get("reflect_round", 0) + 1,
            "reflect_target": target,
            "reflect_history": state.get("reflect_history", [])
            + ([target] if target else []),
            "node_trace": state.get("node_trace", []) + ["reflect"],
        }

    async def writer(state: ResearchState):
        if state.get("scenario") == "writer_error":
            raise RuntimeError("mock writer fixture failed")
        ev = state.get("evidence", [])
        body = await writer_provider.generate(
            state["topic"], ev, state.get("output_format", "narrative")
        )
        if ev:
            body += " [[cite:pending]]"
        if state.get("failed_sources"):
            body += " 有一个来源 Fixture 未能返回，因此覆盖范围有限。"
        return {
            "report_body": body,
            "node_trace": state.get("node_trace", []) + ["writer"],
        }

    async def citation_validator(state: ResearchState):
        if state.get("scenario") == "citation_validation_error":
            raise ValueError("mock citation validation fixture failed")
        return {"node_trace": state.get("node_trace", []) + ["citation_validator"]}

    builder = StateGraph(ResearchState)

    async def tracked(name: str, operation):
        async def invoke(state: ResearchState):
            if on_node_event:
                await on_node_event("node.started", name)
            try:
                result = await operation(state)
            except Exception:
                if on_node_event:
                    await on_node_event("node.failed", name)
                raise
            if on_node_event:
                await on_node_event("node.completed", name)
            return result

        return invoke

    builder.add_node("intent_router", await tracked("intent_router", router))
    builder.add_node("planner", await tracked("planner", planner))
    builder.add_node("scouts", await tracked("scouts", scouts))
    builder.add_node("evidence_judge", await tracked("evidence_judge", evidence_judge))
    builder.add_node("analyst", await tracked("analyst", analyst))
    builder.add_node("reflect", await tracked("reflect", reflect))
    builder.add_node("writer", await tracked("writer", writer))
    builder.add_node(
        "citation_validator", await tracked("citation_validator", citation_validator)
    )
    builder.add_edge(START, "intent_router")
    builder.add_edge("intent_router", "planner")
    builder.add_edge("planner", "scouts")
    builder.add_edge("scouts", "evidence_judge")
    builder.add_edge("evidence_judge", "analyst")
    builder.add_conditional_edges(
        "analyst",
        lambda state: (
            "reflect"
            if state.get("needs_reflection")
            and state.get("reflect_round", 0) < state.get("max_reflect_rounds", 0)
            and state.get("scout_calls_used", 0) < state.get("max_scout_calls", 3)
            else "writer"
        ),
        {"reflect": "reflect", "writer": "writer"},
    )
    builder.add_edge("reflect", "scouts")
    builder.add_edge("writer", "citation_validator")
    builder.add_edge("citation_validator", END)
    graph = builder.compile()
    initial: ResearchState = {
        "topic": topic,
        "output_format": output_format,
        "sources": sources,
        "scenario": scenario or "success",
        "dimensions": dimensions,
        "max_reflect_rounds": max_reflect_rounds,
        "max_scout_calls": max_scout_calls,
        "max_concurrent_scouts": max_concurrent_scouts,
        "time_range": (
            {"start": time_range["start"], "end": time_range["end"]}
            if time_range
            else None
        ),
        "scout_calls_used": 0,
        "reflect_round": 0,
        "evidence": [],
        "failed_sources": [],
        "node_trace": [],
        "attempted_sources": [],
        "reflect_history": [],
    }
    result = initial.copy()
    async for update in graph.astream(initial, stream_mode="updates"):
        for value in update.values():
            result.update(value)
    return result
