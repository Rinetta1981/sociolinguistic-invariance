import json
from pathlib import Path
from typing import Any, cast

from jsonschema import Draft202012Validator

from sociolinguistic_invariance.core import (
    BenchmarkSplit,
    PromptVariant,
    SemanticFamily,
    TaskType,
    ValidationStatus,
    VariationCondition,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCHEMA_PATH = PROJECT_ROOT / "schemas" / "semantic_family.schema.json"


def _load_json_object(path: str | Path) -> dict[str, Any]:
    """Load a JSON file whose top-level value must be an object."""

    json_path = Path(path)

    with json_path.open(encoding="utf-8") as file:
        raw_data: Any = json.load(file)

    if not isinstance(raw_data, dict):
        raise ValueError("JSON file must contain an object")

    return cast(dict[str, Any], raw_data)


def _require_string(record: dict[str, Any], key: str) -> str:
    """Return a required non-empty string field."""

    value = record.get(key)

    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")

    return value


def validate_semantic_family_record(
    record: dict[str, Any],
    schema_path: str | Path = DEFAULT_SCHEMA_PATH,
) -> None:
    """Validate a semantic-family record against the canonical JSON Schema."""

    schema = _load_json_object(schema_path)

    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)

    errors = sorted(
        validator.iter_errors(record),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )

    if errors:
        error = errors[0]
        location = ".".join(str(part) for part in error.absolute_path)

        if location:
            raise ValueError(
                f"schema validation failed at {location}: {error.message}"
            ) from error

        raise ValueError(f"schema validation failed: {error.message}") from error


def semantic_family_from_dict(record: dict[str, Any]) -> SemanticFamily:
    """Convert a dictionary representation into a SemanticFamily."""

    raw_variants = record.get("variants")

    if not isinstance(raw_variants, list):
        raise ValueError("variants must be a list")

    variants: list[PromptVariant] = []

    for raw_variant in raw_variants:
        if not isinstance(raw_variant, dict):
            raise ValueError("each variant must be an object")

        variant_record = cast(dict[str, Any], raw_variant)

        variants.append(
            PromptVariant(
                condition=VariationCondition(
                    _require_string(variant_record, "condition")
                ),
                text=_require_string(variant_record, "text"),
            )
        )

    return SemanticFamily(
        family_id=_require_string(record, "family_id"),
        task_type=TaskType(_require_string(record, "task_type")),
        proposition=_require_string(record, "proposition"),
        domain=_require_string(record, "domain"),
        split=BenchmarkSplit(_require_string(record, "split")),
        expected_behavior=_require_string(record, "expected_behavior"),
        variants=tuple(variants),
        validation_status=ValidationStatus(
            _require_string(record, "validation_status")
        ),
    )


def load_semantic_family(path: str | Path) -> SemanticFamily:
    """Load, schema-validate, and convert one semantic family from JSON."""

    record = _load_json_object(path)

    validate_semantic_family_record(record)

    return semantic_family_from_dict(record)