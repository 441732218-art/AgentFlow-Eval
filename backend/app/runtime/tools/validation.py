# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Input validation for tool arguments against ``input_schema``."""

from __future__ import annotations

from typing import Any

from app.runtime.tools.errors import ToolInputValidationError

_TYPE_CHECKS: dict[str, type | tuple[type, ...]] = {
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "object": dict,
    "array": list,
}


def validate_arguments(input_schema: dict[str, Any], arguments: dict[str, Any]) -> None:
    """Validate ``arguments`` against a JSON-schema-like ``input_schema``.

    Raises:
        ToolInputValidationError: If validation fails.
    """
    if not input_schema:
        return
    if not isinstance(input_schema, dict):
        raise ToolInputValidationError("input_schema must be a dict")
    if not isinstance(arguments, dict):
        raise ToolInputValidationError("arguments must be a dict")

    schema_type = input_schema.get("type")
    if schema_type is None:
        return
    if schema_type != "object":
        raise ToolInputValidationError("Only object input_schema.type is supported")

    for key in input_schema.get("required", []):
        if key not in arguments:
            raise ToolInputValidationError(f"Missing required argument: {key}")

    properties = input_schema.get("properties", {})
    if not isinstance(properties, dict):
        raise ToolInputValidationError("input_schema.properties must be a dict")

    for key, prop_schema in properties.items():
        if key not in arguments:
            continue
        if not isinstance(prop_schema, dict):
            continue
        _validate_value(key, arguments[key], prop_schema)


def _validate_value(field_name: str, value: Any, prop_schema: dict[str, Any]) -> None:
    expected_type = prop_schema.get("type")
    if expected_type is None:
        return
    checker = _TYPE_CHECKS.get(expected_type)
    if checker is None:
        raise ToolInputValidationError(f"Unsupported schema type: {expected_type}")
    if not isinstance(value, checker):
        raise ToolInputValidationError(
            f"Argument '{field_name}' must be of type {expected_type}"
        )
