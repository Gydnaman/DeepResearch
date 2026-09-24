# DeepResearch API

The API implementation lives in `src/deepresearch_api/`. The repository-level README documents the local PostgreSQL setup, environment variables, and the full demo flow.

From the repository root, run database migrations with `uv run --directory backend alembic upgrade head`, start the API with `uv run --directory backend uvicorn deepresearch_api.main:app --host 127.0.0.1 --port 8000`, and run backend tests with `uv run --directory backend pytest`.

Phase A uses deterministic fixtures only. It does not call external model, search, or corpus services.
