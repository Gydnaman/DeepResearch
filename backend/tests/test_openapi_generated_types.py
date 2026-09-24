from pathlib import Path


def test_frontend_api_types_match_generated_openapi_schema():
    project_root = Path(__file__).resolve().parents[2]
    generated_file = project_root / "frontend" / "src" / "api" / "generated.ts"
    assert generated_file.exists(), (
        "Run the OpenAPI TypeScript generator to create generated.ts"
    )

    from deepresearch_api.generate_types import render_types
    from deepresearch_api.main import app

    event_response = app.openapi()["paths"]["/api/v1/research-runs/{run_id}/events"][
        "get"
    ]["responses"]["200"]["content"]["text/event-stream"]["schema"]
    assert event_response == {
        "oneOf": [
            {"$ref": "#/components/schemas/ResearchEvent"},
            {"$ref": "#/components/schemas/StreamControlMessage"},
        ]
    }
    openapi_schema = app.openapi()
    validation_response = openapi_schema["paths"]["/api/v1/research-runs"]["post"][
        "responses"
    ]["422"]["content"]["application/json"]["schema"]
    assert validation_response["$ref"] == "#/components/schemas/ErrorEnvelope"
    run_responses = openapi_schema["paths"]["/api/v1/research-runs/{run_id}"]["get"][
        "responses"
    ]
    assert run_responses["404"]["content"]["application/json"]["schema"]["$ref"] == (
        "#/components/schemas/ErrorEnvelope"
    )
    assert "409" not in run_responses
    report_responses = openapi_schema["paths"]["/api/v1/research-runs/{run_id}/report"][
        "get"
    ]["responses"]
    assert report_responses["409"]["content"]["application/json"]["schema"]["$ref"] == (
        "#/components/schemas/ErrorEnvelope"
    )
    start_responses = openapi_schema["paths"]["/api/v1/research-runs/{run_id}/start"][
        "post"
    ]["responses"]
    assert start_responses["409"]["content"]["application/json"]["schema"]["$ref"] == (
        "#/components/schemas/ErrorEnvelope"
    )
    generated_types = generated_file.read_text(encoding="utf-8")
    assert "StreamControlMessage:" in generated_types
    assert "ErrorEnvelope:" in generated_types
    assert generated_types == render_types(openapi_schema)
