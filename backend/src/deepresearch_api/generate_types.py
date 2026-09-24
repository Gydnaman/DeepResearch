from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any


def _type_name(schema: dict[str, Any]) -> str:
    if "$ref" in schema:
        name = schema["$ref"].rsplit("/", 1)[-1]
        return f"components['schemas']['{name}']"
    if "enum" in schema:
        return " | ".join(repr(value) for value in schema["enum"])
    if "const" in schema:
        return repr(schema["const"])
    if "anyOf" in schema:
        return " | ".join(_type_name(item) for item in schema["anyOf"])
    if "oneOf" in schema:
        return " | ".join(_type_name(item) for item in schema["oneOf"])
    if "allOf" in schema:
        return " & ".join(_type_name(item) for item in schema["allOf"])

    schema_type = schema.get("type")
    if schema_type == "array":
        return f"Array<{_type_name(schema.get('items', {}))}>"
    if schema_type == "object":
        properties = schema.get("properties", {})
        if properties:
            required = set(schema.get("required", []))
            members = [
                f"  {name}{'' if name in required else '?'}: {_type_name(value)}"
                for name, value in properties.items()
            ]
            return "{\n" + ";\n".join(members) + "\n}"
        additional = schema.get("additionalProperties")
        if isinstance(additional, dict):
            return f"Record<string, {_type_name(additional)}>"
        return (
            "Record<string, unknown>"
            if additional is not False
            else "Record<string, never>"
        )
    return {
        "string": "string",
        "integer": "number",
        "number": "number",
        "boolean": "boolean",
        "null": "null",
    }.get(schema_type, "unknown")


def render_types(openapi_schema: dict[str, Any]) -> str:
    schemas = openapi_schema["components"]["schemas"]
    entries = "\n".join(
        f"    {name}: {_type_name(schema)}" for name, schema in sorted(schemas.items())
    )
    return (
        "/* Generated from the FastAPI OpenAPI schema. Do not edit by hand. */\n"
        "export interface components {\n"
        "  schemas: {\n"
        f"{entries}\n"
        "  }\n"
        "}\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate frontend API types from FastAPI OpenAPI"
    )
    parser.add_argument(
        "--check", action="store_true", help="fail if generated types are stale"
    )
    args = parser.parse_args()

    from .main import app

    target = (
        Path(__file__).resolve().parents[3]
        / "frontend"
        / "src"
        / "api"
        / "generated.ts"
    )
    generated = render_types(app.openapi())
    if args.check:
        if not target.exists() or target.read_text(encoding="utf-8") != generated:
            raise SystemExit(
                "Frontend API types are stale; run deepresearch_api.generate_types"
            )
        return
    target.write_text(generated, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
