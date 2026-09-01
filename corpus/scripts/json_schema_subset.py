#!/usr/bin/env python3
"""Small JSON Schema subset used by the dependency-free corpus validator."""
from __future__ import annotations

import json
import re
from datetime import date


class SchemaViolation(ValueError):
    """Raised when an instance violates the supported schema keywords."""


def type_matches(value, expected: str) -> bool:
    return {
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
        "null": value is None,
    }[expected]


def validate_schema(value, schema: dict, path: str = "$") -> None:
    if "const" in schema and value != schema["const"]:
        raise SchemaViolation(f"{path}: expected constant {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        raise SchemaViolation(f"{path}: value {value!r} is outside the enum")

    expected = schema.get("type")
    if expected is not None:
        allowed = expected if isinstance(expected, list) else [expected]
        if not any(type_matches(value, item) for item in allowed):
            raise SchemaViolation(f"{path}: expected type {allowed}, got {type(value).__name__}")

    if isinstance(value, dict):
        required = set(schema.get("required", []))
        missing = sorted(required - set(value))
        if missing:
            raise SchemaViolation(f"{path}: missing required properties {missing}")
        if "minProperties" in schema and len(value) < schema["minProperties"]:
            raise SchemaViolation(f"{path}: requires at least {schema['minProperties']} properties")
        properties = schema.get("properties", {})
        additional = schema.get("additionalProperties", True)
        for key, item in value.items():
            if key in properties:
                validate_schema(item, properties[key], f"{path}.{key}")
            elif additional is False:
                raise SchemaViolation(f"{path}: unexpected property {key!r}")
            elif isinstance(additional, dict):
                validate_schema(item, additional, f"{path}.{key}")

    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            raise SchemaViolation(f"{path}: requires at least {schema['minItems']} items")
        if schema.get("uniqueItems"):
            encoded = [json.dumps(item, sort_keys=True, ensure_ascii=False) for item in value]
            if len(encoded) != len(set(encoded)):
                raise SchemaViolation(f"{path}: items must be unique")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                validate_schema(item, item_schema, f"{path}[{index}]")

    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            raise SchemaViolation(f"{path}: requires at least {schema['minLength']} characters")
        if "pattern" in schema and re.search(schema["pattern"], value) is None:
            raise SchemaViolation(f"{path}: does not match {schema['pattern']!r}")
        if schema.get("format") == "date":
            try:
                date.fromisoformat(value)
            except ValueError as exc:
                raise SchemaViolation(f"{path}: invalid ISO date") from exc

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            raise SchemaViolation(f"{path}: below minimum {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            raise SchemaViolation(f"{path}: above maximum {schema['maximum']}")
