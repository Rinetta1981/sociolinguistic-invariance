from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from types import SimpleNamespace
from typing import cast

from sociolinguistic_invariance.dashboard_data import (
    DASHBOARD_DATA_FORMAT_VERSION,
)


def _require_mapping(
    value: object,
    *,
    context: str,
) -> Mapping[str, object]:
    """Require a JSON object."""
    if not isinstance(value, Mapping):
        raise ValueError(
            f"{context} must be a JSON object."
        )

    return cast(
        Mapping[str, object],
        value,
    )


def _require_list(
    mapping: Mapping[str, object],
    field: str,
    *,
    context: str,
) -> list[object]:
    """Require a JSON array field."""
    value = mapping.get(field)

    if not isinstance(value, list):
        raise ValueError(
            f"{context}.{field} must be a JSON array."
        )

    return cast(
        list[object],
        value,
    )


def _require_string(
    mapping: Mapping[str, object],
    field: str,
    *,
    context: str,
) -> str:
    """Require a non-empty string field."""
    value = mapping.get(field)

    if not isinstance(value, str):
        raise ValueError(
            f"{context}.{field} must be a string."
        )

    if not value.strip():
        raise ValueError(
            f"{context}.{field} must not be blank."
        )

    return value


def _optional_string(
    mapping: Mapping[str, object],
    field: str,
    *,
    context: str,
) -> str | None:
    """Read an optional string field."""
    value = mapping.get(field)

    if value is None:
        return None

    if not isinstance(value, str):
        raise ValueError(
            f"{context}.{field} must be a string or null."
        )

    return value


def _require_bool(
    mapping: Mapping[str, object],
    field: str,
    *,
    context: str,
) -> bool:
    """Require a Boolean field."""
    value = mapping.get(field)

    if not isinstance(value, bool):
        raise ValueError(
            f"{context}.{field} must be a Boolean."
        )

    return value


def _require_int(
    mapping: Mapping[str, object],
    field: str,
    *,
    context: str,
) -> int:
    """Require a non-negative integer field."""
    value = mapping.get(field)

    if isinstance(value, bool) or not isinstance(
        value,
        int,
    ):
        raise ValueError(
            f"{context}.{field} must be an integer."
        )

    if value < 0:
        raise ValueError(
            f"{context}.{field} must not be negative."
        )

    return value


def _optional_int(
    mapping: Mapping[str, object],
    field: str,
    *,
    context: str,
) -> int | None:
    """Read an optional non-negative integer field."""
    value = mapping.get(field)

    if value is None:
        return None

    if isinstance(value, bool) or not isinstance(
        value,
        int,
    ):
        raise ValueError(
            f"{context}.{field} must be an integer or null."
        )

    if value < 0:
        raise ValueError(
            f"{context}.{field} must not be negative."
        )

    return value


def _optional_number(
    mapping: Mapping[str, object],
    field: str,
    *,
    context: str,
) -> float | None:
    """Read an optional numeric field."""
    value = mapping.get(field)

    if value is None:
        return None

    if isinstance(value, bool) or not isinstance(
        value,
        int | float,
    ):
        raise ValueError(
            f"{context}.{field} must be numeric or null."
        )

    if value < 0:
        raise ValueError(
            f"{context}.{field} must not be negative."
        )

    return float(value)


def _response_namespace(
    value: object,
    *,
    family_id: str,
    index: int,
) -> SimpleNamespace:
    """Validate and convert one response."""
    context = (
        f"family {family_id!r} response {index}"
    )

    mapping = _require_mapping(
        value,
        context=context,
    )

    request_id = _require_string(
        mapping,
        "request_id",
        context=context,
    )

    condition = _require_string(
        mapping,
        "condition",
        context=context,
    )

    prompt_text = _require_string(
        mapping,
        "prompt_text",
        context=context,
    )

    response_text = _require_string(
        mapping,
        "response_text",
        context=context,
    )

    response_outcome = _require_string(
        mapping,
        "response_outcome",
        context=context,
    )

    standard_contrast = _optional_string(
        mapping,
        "standard_contrast",
        context=context,
    )

    response_sha256 = _require_string(
        mapping,
        "response_sha256",
        context=context,
    )

    calculated_sha256 = hashlib.sha256(
        response_text.encode("utf-8")
    ).hexdigest()

    if response_sha256 != calculated_sha256:
        raise ValueError(
            f"{context}.response_sha256 does not match "
            "the exact response text."
        )

    provider = _require_string(
        mapping,
        "provider",
        context=context,
    )

    requested_model = _require_string(
        mapping,
        "requested_model",
        context=context,
    )

    returned_model = _optional_string(
        mapping,
        "returned_model",
        context=context,
    )

    finish_reason = _optional_string(
        mapping,
        "finish_reason",
        context=context,
    )

    latency_seconds = _optional_number(
        mapping,
        "latency_seconds",
        context=context,
    )

    input_tokens = _optional_int(
        mapping,
        "input_tokens",
        context=context,
    )

    output_tokens = _optional_int(
        mapping,
        "output_tokens",
        context=context,
    )

    total_tokens = _optional_int(
        mapping,
        "total_tokens",
        context=context,
    )

    return SimpleNamespace(
        request_id=request_id,
        condition=condition,
        prompt_text=prompt_text,
        response_text=response_text,
        response_outcome=response_outcome,
        standard_contrast=standard_contrast,
        response_sha256=response_sha256,
        provider=provider,
        requested_model=requested_model,
        returned_model=returned_model,
        finish_reason=finish_reason,
        latency_seconds=latency_seconds,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
    )


def _family_namespace(
    value: object,
    *,
    index: int,
) -> SimpleNamespace:
    """Validate and convert one semantic family."""
    context = f"family {index}"

    mapping = _require_mapping(
        value,
        context=context,
    )

    family_id = _require_string(
        mapping,
        "family_id",
        context=context,
    )

    task_type = _require_string(
        mapping,
        "task_type",
        context=context,
    )

    rubric_version = _require_string(
        mapping,
        "rubric_version",
        context=context,
    )

    family_outcome = _require_string(
        mapping,
        "family_outcome",
        context=context,
    )

    raw_responses = _require_list(
        mapping,
        "responses",
        context=context,
    )

    responses = tuple(
        _response_namespace(
            response,
            family_id=family_id,
            index=response_index,
        )
        for response_index, response in enumerate(
            raw_responses,
        )
    )

    conditions = [
        response.condition
        for response in responses
    ]

    if len(conditions) != len(set(conditions)):
        raise ValueError(
            f"Family {family_id!r} contains duplicate conditions."
        )

    return SimpleNamespace(
        family_id=family_id,
        task_type=task_type,
        rubric_version=rubric_version,
        family_outcome=family_outcome,
        responses=responses,
    )


def load_dashboard_snapshot(
    path: Path,
) -> SimpleNamespace:
    """Load and validate a portable dashboard snapshot."""
    raw_payload: object = json.loads(
        path.read_text(
            encoding="utf-8",
        )
    )

    payload = _require_mapping(
        raw_payload,
        context="dashboard snapshot",
    )

    format_version = _require_string(
        payload,
        "dashboard_data_format_version",
        context="dashboard snapshot",
    )

    if format_version != DASHBOARD_DATA_FORMAT_VERSION:
        raise ValueError(
            "Unsupported dashboard snapshot format: "
            f"{format_version!r}."
        )

    run_id = _require_string(
        payload,
        "run_id",
        context="dashboard snapshot",
    )

    annotator_id = _require_string(
        payload,
        "annotator_id",
        context="dashboard snapshot",
    )

    benchmark_claim_eligible = _require_bool(
        payload,
        "benchmark_claim_eligible",
        context="dashboard snapshot",
    )

    annotation_protocol_version = _require_string(
        payload,
        "annotation_protocol_version",
        context="dashboard snapshot",
    )

    scoring_protocol_version = _require_string(
        payload,
        "scoring_protocol_version",
        context="dashboard snapshot",
    )

    family_count = _require_int(
        payload,
        "family_count",
        context="dashboard snapshot",
    )

    response_count = _require_int(
        payload,
        "response_count",
        context="dashboard snapshot",
    )

    raw_families = _require_list(
        payload,
        "families",
        context="dashboard snapshot",
    )

    families = tuple(
        _family_namespace(
            family,
            index=family_index,
        )
        for family_index, family in enumerate(
            raw_families,
        )
    )

    if family_count != len(families):
        raise ValueError(
            "Dashboard snapshot family_count does not match "
            "the number of serialized families."
        )

    actual_response_count = sum(
        len(family.responses)
        for family in families
    )

    if response_count != actual_response_count:
        raise ValueError(
            "Dashboard snapshot response_count does not match "
            "the number of serialized responses."
        )

    family_ids = [
        family.family_id
        for family in families
    ]

    if len(family_ids) != len(set(family_ids)):
        raise ValueError(
            "Dashboard snapshot contains duplicate family IDs."
        )

    return SimpleNamespace(
        dashboard_data_format_version=format_version,
        run_id=run_id,
        annotator_id=annotator_id,
        benchmark_claim_eligible=benchmark_claim_eligible,
        annotation_protocol_version=annotation_protocol_version,
        scoring_protocol_version=scoring_protocol_version,
        family_count=family_count,
        response_count=response_count,
        families=families,
    )