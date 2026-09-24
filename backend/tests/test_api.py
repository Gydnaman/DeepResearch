import json
import time

from fastapi.testclient import TestClient

from deepresearch_api.models import ResearchRunRow
from deepresearch_api.service import create_app


def make_app(tmp_path, *, scenarios_enabled=False):
    database = tmp_path / "api.sqlite"
    return create_app(
        f"sqlite+aiosqlite:///{database.as_posix()}",
        scenarios_enabled=scenarios_enabled,
    )


def create(client, **overrides):
    payload = {
        "topic": "renewable energy storage",
        "sources": {"web": True, "local": True},
        "output_format": "narrative",
        "dimensions": ["cost", "reliability"],
    }
    payload.update(overrides)
    return client.post("/api/v1/research-runs", json=payload)


def wait_for_terminal(client, run_id, timeout=5):
    until = time.monotonic() + timeout
    while time.monotonic() < until:
        response = client.get(f"/api/v1/research-runs/{run_id}")
        if response.json()["status"] in {"completed", "failed", "cancelled"}:
            return response.json()
        time.sleep(0.025)
    raise AssertionError("run did not reach a terminal status")


def test_create_start_and_trace_report_citations(tmp_path):
    with TestClient(make_app(tmp_path)) as client:
        created = create(client)
        assert created.status_code == 201
        payload = created.json()
        run_id = payload["run"]["run_id"]
        assert payload["run"]["status"] == "planned"
        assert payload["run"]["fixture"] is True
        assert client.get(f"/api/v1/research-runs/{run_id}/plan").status_code == 200

        started = client.post(f"/api/v1/research-runs/{run_id}/start", json={})
        assert started.status_code == 200
        terminal = wait_for_terminal(client, run_id)
        assert terminal["status"] == "completed"

        evidence = client.get(f"/api/v1/research-runs/{run_id}/evidence").json()
        report = client.get(f"/api/v1/research-runs/{run_id}/report").json()
        assert evidence
        assert report["mode"] == "mock"
        assert all(citation["run_id"] == run_id for citation in report["citations"])
        assert {citation["evidence_id"] for citation in report["citations"]} <= {
            item["evidence_id"] for item in evidence
        }
        assert all(
            len(section["citation_ids"]) == section["body"].count("[[cite:")
            for section in report["sections"]
        )
        assert all(
            task["status"] in {"completed", "skipped"}
            for task in client.get(
                f"/api/v1/research-runs/{run_id}/search-tasks"
            ).json()
        )

        replay = client.get(
            f"/api/v1/research-runs/{run_id}/events", headers={"Last-Event-ID": "0"}
        )
        assert replay.status_code == 200
        assert "event: plan.ready" in replay.text
        assert "event: run.completed" in replay.text
        assert "id: 1" in replay.text
        ids = [
            int(line[4:])
            for line in replay.text.splitlines()
            if line.startswith("id: ")
        ]
        resume = client.get(
            f"/api/v1/research-runs/{run_id}/events",
            headers={"Last-Event-ID": str(ids[2])},
        )
        resumed_ids = [
            int(line[4:])
            for line in resume.text.splitlines()
            if line.startswith("id: ")
        ]
        assert resumed_ids and min(resumed_ids) > ids[2]


def test_planned_cancel_is_terminal_and_has_no_report(tmp_path):
    with TestClient(make_app(tmp_path)) as client:
        run_id = create(client).json()["run"]["run_id"]
        response = client.post(f"/api/v1/research-runs/{run_id}/cancel", json={})
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"
        assert client.get(f"/api/v1/research-runs/{run_id}/report").status_code == 409
        events = client.get(f"/api/v1/research-runs/{run_id}/events").text
        assert "event: run.cancelled" in events


def test_disabled_scenario_is_rejected_and_bad_event_cursor_is_idless(tmp_path):
    with TestClient(make_app(tmp_path)) as client:
        rejected = create(client, scenario="no_results")
        assert rejected.status_code == 422
        invalid_topic = create(client, topic="   ")
        assert invalid_topic.status_code == 422
        assert invalid_topic.json()["error"]["code"] == "validation_error"
        run_id = create(client).json()["run"]["run_id"]
        response = client.get(f"/api/v1/research-runs/{run_id}/events?after=99")
        assert response.status_code == 200
        assert "event: stream.error" in response.text
        assert "invalid_event_cursor" in response.text
        assert "id:" not in response.text


def test_time_range_excludes_fixture_evidence_from_report(tmp_path):
    with TestClient(make_app(tmp_path)) as client:
        run_id = create(
            client,
            time_range={"start": "2030-01-01", "end": "2030-01-31"},
        ).json()["run"]["run_id"]
        client.post(f"/api/v1/research-runs/{run_id}/start", json={})

        assert wait_for_terminal(client, run_id)["status"] == "completed"
        assert client.get(f"/api/v1/research-runs/{run_id}/evidence").json() == []
        report = client.get(f"/api/v1/research-runs/{run_id}/report").json()
        assert report["warning"] == "no_evidence"
        assert report["citations"] == []


def test_time_range_keeps_matching_fixture_evidence_and_citations(tmp_path):
    with TestClient(make_app(tmp_path)) as client:
        run_id = create(
            client,
            time_range={"start": "2025-03-01", "end": "2025-03-31"},
        ).json()["run"]["run_id"]
        client.post(f"/api/v1/research-runs/{run_id}/start", json={})

        assert wait_for_terminal(client, run_id)["status"] == "completed"
        evidence = client.get(f"/api/v1/research-runs/{run_id}/evidence").json()
        report = client.get(f"/api/v1/research-runs/{run_id}/report").json()

        assert [item["published_at"] for item in evidence] == ["2025-03-14"]
        assert len(report["citations"]) == 1
        assert report["citations"][0]["evidence_id"] == evidence[0]["evidence_id"]


def test_unrelated_topic_uses_clearly_synthetic_fixture_content(tmp_path):
    with TestClient(make_app(tmp_path)) as client:
        run_id = create(client, topic="How do guitars work?").json()["run"]["run_id"]
        client.post(f"/api/v1/research-runs/{run_id}/start", json={})
        assert wait_for_terminal(client, run_id)["status"] == "completed"

        evidence = client.get(f"/api/v1/research-runs/{run_id}/evidence").json()
        report = client.get(f"/api/v1/research-runs/{run_id}/report").json()
        assert evidence
        assert all(
            "International Energy Agency" not in row["source_label"] for row in evidence
        )
        assert all(
            "National Renewable Energy Laboratory" not in row["source_label"]
            for row in evidence
        )
        assert all("合成占位" in row["excerpt"] for row in evidence)
        assert "不构成关于该主题的研究结论" in report["sections"][0]["body"]


def test_unbounded_event_cursor_returns_control_error_without_server_failure(tmp_path):
    with TestClient(make_app(tmp_path)) as client:
        run_id = create(client).json()["run"]["run_id"]
        response = client.get(
            f"/api/v1/research-runs/{run_id}/events",
            headers={"Last-Event-ID": "9" * 5000},
        )

        assert response.status_code == 200
        assert "event: stream.error" in response.text
        assert "invalid_event_cursor" in response.text


def test_idle_event_stream_sends_sse_comment_keepalive(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "deepresearch_api.service.SSE_KEEPALIVE_SECONDS", 0, raising=False
    )
    with TestClient(make_app(tmp_path, scenarios_enabled=True)) as client:
        run_id = create(client, scenario="cancel").json()["run"]["run_id"]
        client.post(f"/api/v1/research-runs/{run_id}/start", json={})

        response = client.get(f"/api/v1/research-runs/{run_id}/events?after=0")

        assert response.status_code == 200
        assert ": keep-alive" in response.text
        assert "event: run.cancelled" in response.text


def test_validation_error_names_field_without_echoing_input(tmp_path):
    with TestClient(make_app(tmp_path)) as client:
        response = create(client, dimensions=["cost"] * 13)

        assert response.status_code == 422
        message = response.json()["error"]["message"]
        assert "dimensions" in message
        assert "12" in message
        assert "cost" not in message


def test_history_cursor_is_stable_and_invalid_cursor_is_rejected(tmp_path):
    with TestClient(make_app(tmp_path)) as client:
        for index in range(3):
            create(client, topic=f"topic {index}")
        first = client.get("/api/v1/research-runs?limit=2").json()
        assert len(first["items"]) == 2
        assert first["next_cursor"]
        create(client, topic="new item after snapshot")
        second = client.get(
            "/api/v1/research-runs?limit=2&cursor=" + first["next_cursor"]
        ).json()
        assert len(second["items"]) == 1
        assert {item["run_id"] for item in first["items"]}.isdisjoint(
            item["run_id"] for item in second["items"]
        )
        assert client.get("/api/v1/research-runs?cursor=bad").status_code == 422


def test_source_toggles_and_scout_budget_are_visible_in_plan_and_tasks(tmp_path):
    with TestClient(make_app(tmp_path)) as client:
        run_id = create(
            client,
            sources={"web": True, "local": False},
            budgets={"max_scout_calls": 1},
        ).json()["run"]["run_id"]
        plan = client.get(f"/api/v1/research-runs/{run_id}/plan").json()
        assert (
            next(step for step in plan["steps"] if step.get("source") == "local")[
                "status"
            ]
            == "skipped"
        )
        client.post(f"/api/v1/research-runs/{run_id}/start", json={})
        assert wait_for_terminal(client, run_id)["status"] == "completed"
        replay = client.get(f"/api/v1/research-runs/{run_id}/events?after=0").text
        assert "event: node.skipped" in replay
        tasks = client.get(f"/api/v1/research-runs/{run_id}/search-tasks").json()
        assert {task["source"]: task["status"] for task in tasks} == {
            "local": "skipped",
            "web": "completed",
        }


def test_no_results_and_partial_failure_are_explicit_fixtures(tmp_path):
    with TestClient(make_app(tmp_path, scenarios_enabled=True)) as client:
        no_results_id = create(client, scenario="no_results").json()["run"]["run_id"]
        client.post(f"/api/v1/research-runs/{no_results_id}/start", json={})
        assert wait_for_terminal(client, no_results_id)["status"] == "completed"
        no_results = client.get(f"/api/v1/research-runs/{no_results_id}/report").json()
        assert no_results["warning"] == "no_evidence"
        assert no_results["citations"] == []

        partial_id = create(client, scenario="partial_scout_failure").json()["run"][
            "run_id"
        ]
        client.post(f"/api/v1/research-runs/{partial_id}/start", json={})
        assert wait_for_terminal(client, partial_id)["status"] == "completed"
        tasks = client.get(f"/api/v1/research-runs/{partial_id}/search-tasks").json()
        assert {task["status"] for task in tasks} == {"completed", "failed"}
        report = client.get(f"/api/v1/research-runs/{partial_id}/report").json()
        assert report["warning"] == "partial_sources"
        assert "覆盖范围有限" in report["sections"][0]["body"]


def test_queued_cancel_closes_precreated_search_tasks(tmp_path):
    app = make_app(tmp_path)
    with TestClient(app) as client:
        run_id = create(client).json()["run"]["run_id"]

        async def mark_queued_without_worker():
            async with app.state.sessions() as session, session.begin():
                row = await session.get(ResearchRunRow, run_id)
                row.status = "queued"

        client.portal.call(mark_queued_without_worker)
        cancelled = client.post(f"/api/v1/research-runs/{run_id}/cancel", json={})

        assert cancelled.json()["status"] == "cancelled"
        tasks = client.get(f"/api/v1/research-runs/{run_id}/search-tasks").json()
        assert {task["status"] for task in tasks} == {"cancelled"}


def test_failure_of_every_attempted_scout_produces_no_report(tmp_path):
    with TestClient(make_app(tmp_path, scenarios_enabled=True)) as client:
        run_id = create(
            client, scenario="partial_scout_failure", budgets={"max_scout_calls": 1}
        ).json()["run"]["run_id"]
        client.post(f"/api/v1/research-runs/{run_id}/start", json={})
        failed = wait_for_terminal(client, run_id)
        assert failed["status"] == "failed"
        assert client.get(f"/api/v1/research-runs/{run_id}/report").status_code == 409
        tasks = client.get(f"/api/v1/research-runs/{run_id}/search-tasks").json()
        assert {task["status"] for task in tasks} == {"failed", "skipped"}


def test_writer_failure_does_not_publish_report(tmp_path):
    with TestClient(make_app(tmp_path, scenarios_enabled=True)) as client:
        run_id = create(client, scenario="writer_error").json()["run"]["run_id"]
        client.post(f"/api/v1/research-runs/{run_id}/start", json={})
        assert wait_for_terminal(client, run_id)["status"] == "failed"
        assert client.get(f"/api/v1/research-runs/{run_id}/report").status_code == 409
        tasks = client.get(f"/api/v1/research-runs/{run_id}/search-tasks").json()
        assert {task["status"] for task in tasks} == {"failed"}
        assert {task["error"] for task in tasks} == {"runtime_failed"}


def test_reflect_is_bounded_and_persisted_as_a_follow_up_task(tmp_path):
    with TestClient(make_app(tmp_path, scenarios_enabled=True)) as client:
        run_id = create(client, dimensions=["cost", "coverage"]).json()["run"]["run_id"]
        client.post(f"/api/v1/research-runs/{run_id}/start", json={})
        assert wait_for_terminal(client, run_id)["status"] == "completed"
        tasks = client.get(f"/api/v1/research-runs/{run_id}/search-tasks").json()
        assert len(tasks) == 3
        assert sum("Reflect" in task["query_label"] for task in tasks) == 1
        reflect_task = next(task for task in tasks if "Reflect" in task["query_label"])
        assert reflect_task["evidence_ids"] == []

        events = [
            json.loads(line[6:])
            for line in client.get(
                f"/api/v1/research-runs/{run_id}/events?after=0"
            ).text.splitlines()
            if line.startswith("data: ")
        ]
        reflect_started = next(
            event
            for event in events
            if event["event"] == "search_task.started"
            and event["task_id"] == reflect_task["task_id"]
        )
        scout_starts = [
            event
            for event in events
            if event["event"] == "node.started" and event["node"] == "scouts"
        ]
        assert len(scout_starts) == 2
        assert reflect_started["id"] < scout_starts[1]["id"]
        assert (
            sum(
                event["event"] == "search_task.completed"
                and event["task_id"] == reflect_task["task_id"]
                for event in events
            )
            == 1
        )


def test_cancel_scenario_and_citation_error_end_without_report(tmp_path):
    with TestClient(make_app(tmp_path, scenarios_enabled=True)) as client:
        cancel_id = create(client, scenario="cancel").json()["run"]["run_id"]
        client.post(f"/api/v1/research-runs/{cancel_id}/start", json={})
        assert wait_for_terminal(client, cancel_id)["status"] == "cancelled"
        assert (
            client.get(f"/api/v1/research-runs/{cancel_id}/report").status_code == 409
        )

        citation_id = create(client, scenario="citation_validation_error").json()[
            "run"
        ]["run_id"]
        client.post(f"/api/v1/research-runs/{citation_id}/start", json={})
        failed = wait_for_terminal(client, citation_id)
        assert failed["status"] == "failed"
        assert failed["failure_code"] == "citation_invalid_reference"
        assert (
            client.get(f"/api/v1/research-runs/{citation_id}/report").status_code == 409
        )


def test_duplicate_start_and_cancel_completion_race_have_one_terminal_event(tmp_path):
    with TestClient(make_app(tmp_path, scenarios_enabled=True)) as client:
        run_id = create(client).json()["run"]["run_id"]
        first = client.post(f"/api/v1/research-runs/{run_id}/start", json={})
        second = client.post(f"/api/v1/research-runs/{run_id}/start", json={})
        assert first.status_code == 200
        assert second.status_code in {200, 409}
        assert wait_for_terminal(client, run_id)["status"] == "completed"
        events = client.get(f"/api/v1/research-runs/{run_id}/events?after=0").text
        assert events.count("event: run.started") == 1
        assert (
            sum(
                events.count(f"event: run.{name}")
                for name in ("completed", "failed", "cancelled")
            )
            == 1
        )
        ids = [int(line[4:]) for line in events.splitlines() if line.startswith("id: ")]
        assert ids == sorted(set(ids)) and max(ids) <= 100

        cancel_id = create(client, scenario="cancel").json()["run"]["run_id"]
        client.post(f"/api/v1/research-runs/{cancel_id}/start", json={})
        time.sleep(0.05)
        client.post(f"/api/v1/research-runs/{cancel_id}/cancel", json={})
        assert wait_for_terminal(client, cancel_id)["status"] == "cancelled"
        cancel_events = client.get(
            f"/api/v1/research-runs/{cancel_id}/events?after=0"
        ).text
        assert cancel_events.count("event: run.cancelled") == 1
        assert "event: run.completed" not in cancel_events


def test_api_errors_use_a_stable_envelope(tmp_path):
    with TestClient(make_app(tmp_path)) as client:
        assert client.get(
            "/api/v1/research-runs/00000000-0000-0000-0000-000000000000"
        ).json() == {
            "error": {
                "code": "run_not_found",
                "message": "Research run was not found.",
                "retryable": False,
            }
        }


def test_startup_marks_interrupted_runs_failed(tmp_path):
    database_url = f"sqlite+aiosqlite:///{(tmp_path / 'restart.sqlite').as_posix()}"
    with TestClient(create_app(database_url, scenarios_enabled=True)) as client:
        run_id = create(client, scenario="cancel").json()["run"]["run_id"]
        client.post(f"/api/v1/research-runs/{run_id}/start", json={})
        time.sleep(0.05)

    with TestClient(create_app(database_url)) as restarted:
        run = restarted.get(f"/api/v1/research-runs/{run_id}").json()
        assert run["status"] == "failed"
        assert run["failure_code"] == "process_restarted"
        events = restarted.get(f"/api/v1/research-runs/{run_id}/events?after=0").text
        assert "event: run.failed" in events
        tasks = restarted.get(f"/api/v1/research-runs/{run_id}/search-tasks").json()
        assert tasks
        assert {task["status"] for task in tasks} == {"failed"}
        assert {task["error"] for task in tasks} == {"process_restarted"}
