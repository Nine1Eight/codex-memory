"""Competition adapter driven exclusively by a supplied local official schema."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from src.models.canonical import canonical_json, stable_hash


class SubmissionError(ValueError):
    pass


class SubmissionAdapter:
    def __init__(self, schema_path: Path) -> None:
        if not schema_path.is_file():
            raise SubmissionError(
                "official local competition schema is unavailable; core evaluation remains usable"
            )
        try:
            self.schema = json.loads(schema_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SubmissionError(f"invalid official schema: {exc}") from exc
        if not isinstance(self.schema, dict) or self.schema.get("type") != "object":
            raise SubmissionError("official schema must define a top-level object")

    def validate(self, artifact: dict[str, Any]) -> None:
        self._validate_schema_node(self.schema, artifact, "$")

    def _validate_schema_node(self, schema: dict[str, Any], value: Any, path: str) -> None:
        expected_type = schema.get("type")
        if expected_type is not None:
            self._validate_type(expected_type, value, path)
        if "const" in schema and value != schema["const"]:
            raise SubmissionError(f"{path} must equal the official constant value")
        if "enum" in schema and value not in schema["enum"]:
            raise SubmissionError(f"{path} must be one of the official enum values")
        if isinstance(value, dict):
            self._validate_object(schema, value, path)
        elif isinstance(value, list):
            self._validate_array(schema, value, path)
        elif isinstance(value, str):
            self._validate_string(schema, value, path)
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            self._validate_number(schema, value, path)

    def _validate_type(self, expected_type: str, value: Any, path: str) -> None:
        if expected_type == "object":
            valid = isinstance(value, dict)
        elif expected_type == "array":
            valid = isinstance(value, list)
        elif expected_type == "string":
            valid = isinstance(value, str)
        elif expected_type == "integer":
            valid = isinstance(value, int) and not isinstance(value, bool)
        elif expected_type == "number":
            valid = isinstance(value, (int, float)) and not isinstance(value, bool)
        elif expected_type == "boolean":
            valid = isinstance(value, bool)
        elif expected_type == "null":
            valid = value is None
        else:
            raise SubmissionError(f"unsupported official schema type at {path}: {expected_type!r}")
        if not valid:
            raise SubmissionError(f"{path} does not match official type {expected_type}")

    def _validate_object(self, schema: dict[str, Any], value: dict[str, Any], path: str) -> None:
        required = schema.get("required", [])
        if required and not isinstance(required, list):
            raise SubmissionError(f"{path} official required field must be a list")
        missing = [field for field in required if field not in value]
        if missing:
            raise SubmissionError(f"{path} missing official fields: {missing}")
        properties = schema.get("properties", {})
        if properties and not isinstance(properties, dict):
            raise SubmissionError(f"{path} official properties field must be an object")
        if schema.get("additionalProperties") is False:
            extra = sorted(set(value) - set(properties))
            if extra:
                raise SubmissionError(
                    f"{path} contains fields absent from official schema: {extra}"
                )
        minimum = schema.get("minProperties")
        if isinstance(minimum, int) and len(value) < minimum:
            raise SubmissionError(f"{path} is below the official field-count minimum")
        maximum = schema.get("maxProperties")
        if isinstance(maximum, int) and len(value) > maximum:
            raise SubmissionError(f"{path} exceeds the official field-count limit")
        for key, item in value.items():
            if key in properties:
                self._validate_schema_node(properties[key], item, f"{path}.{key}")

    def _validate_array(self, schema: dict[str, Any], value: list[Any], path: str) -> None:
        minimum = schema.get("minItems")
        if isinstance(minimum, int) and len(value) < minimum:
            raise SubmissionError(f"{path} is below the official item-count minimum")
        maximum = schema.get("maxItems")
        if isinstance(maximum, int) and len(value) > maximum:
            raise SubmissionError(f"{path} exceeds the official item-count limit")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                self._validate_schema_node(item_schema, item, f"{path}[{index}]")

    def _validate_string(self, schema: dict[str, Any], value: str, path: str) -> None:
        minimum = schema.get("minLength")
        if isinstance(minimum, int) and len(value) < minimum:
            raise SubmissionError(f"{path} is shorter than the official minimum length")
        maximum = schema.get("maxLength")
        if isinstance(maximum, int) and len(value) > maximum:
            raise SubmissionError(f"{path} exceeds the official maximum length")
        pattern = schema.get("pattern")
        if isinstance(pattern, str) and re.search(pattern, value) is None:
            raise SubmissionError(f"{path} does not match the official pattern")

    def _validate_number(self, schema: dict[str, Any], value: int | float, path: str) -> None:
        minimum = schema.get("minimum")
        if isinstance(minimum, (int, float)) and value < minimum:
            raise SubmissionError(f"{path} is below the official minimum value")
        maximum = schema.get("maximum")
        if isinstance(maximum, (int, float)) and value > maximum:
            raise SubmissionError(f"{path} exceeds the official maximum value")

    def build(
        self, artifact: dict[str, Any], replayable: bool, duplicate: bool = False
    ) -> tuple[str, dict[str, Any]]:
        if not replayable:
            raise SubmissionError("non-replayable findings cannot be submitted")
        if duplicate:
            raise SubmissionError("duplicate findings cannot be submitted")
        self.validate(artifact)
        payload = canonical_json(artifact)
        manifest = {
            "framework_version": "0.1.0",
            "artifact_sha256": stable_hash(artifact),
            "schema_sha256": stable_hash(self.schema),
            "replayable": True,
            "validation": "passed",
        }
        return payload, manifest
