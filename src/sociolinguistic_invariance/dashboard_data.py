from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, cast

from sociolinguistic_invariance.core import (
    TaskType,
    VariationCondition,
)
from sociolinguistic_invariance.pilot_analysis import (
    EXPECTED_CONDITIONS,
    PilotAnalysis,
    analyze_annotation_paths,
)
from sociolinguistic_invariance.scoring import (
    FamilyOutcome,
    ResponseOutcome,
    StandardContrastOutcome,
)

DASHBOARD_DATA_FORMAT_VERSION: Final = (
    "dashboard-data-v0.1"
)


@dataclass(
    frozen=True,
    slots=True,
)
class AnnotationSourceRecord:
    """Normalized content from one annotation-source artifact."""

    source_path: Path
    artifact_type: str
    source_format_version: str
    benchmark_claim_eligible: bool
    run_id: str
    request_id: str
    family_id: str
    task_type: TaskType
    condition: VariationCondition
    prompt_sha256: str
    prompt_text: str
    response_text: str
    provider: str
    requested_model: str
    returned_model: str | None
    finish_reason: str | None
    latency_seconds: float | None
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None


@dataclass(
    frozen=True,
    slots=True,
)
class DashboardResponse:
    """One condition-specific response prepared for a dashboard."""

    request_id: str
    family_id: str
    task_type: TaskType
    condition: VariationCondition
    prompt_text: str
    response_text: str
    response_outcome: ResponseOutcome
    standard_contrast: StandardContrastOutcome | None
    response_sha256: str
    provider: str
    requested_model: str
    returned_model: str | None
    finish_reason: str | None
    latency_seconds: float | None
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None


@dataclass(
    frozen=True,
    slots=True,
)
class DashboardFamily:
    """One semantic family prepared for presentation."""

    family_id: str
    task_type: TaskType
    rubric_version: str
    family_outcome: FamilyOutcome
    responses: tuple[DashboardResponse, ...]


@dataclass(
    frozen=True,
    slots=True,
)
class DashboardDataset:
    """Validated data consumed by the future dashboard UI."""

    format_version: str
    run_id: str
    annotator_id: str
    benchmark_claim_eligible: bool
    annotation_protocol_version: str
    scoring_protocol_version: str
    families: tuple[DashboardFamily, ...]


def _require_mapping(
    value: object,
    *,
    field_name: str,
) -> Mapping[str, object]:
    """Require a JSON object."""

    if not isinstance(
        value,
        dict,
    ):
        raise ValueError(
            f"{field_name} must be a JSON object."
        )

    return cast(
        Mapping[str, object],
        value,
    )


def _require_field(
    record: Mapping[str, object],
    field_name: str,
) -> object:
    """Require one field from a mapping."""

    if field_name not in record:
        raise ValueError(
            f"Missing required field: {field_name}."
        )

    return record[field_name]


def _require_string(
    value: object,
    *,
    field_name: str,
) -> str:
    """Require a non-blank string."""

    if (
        not isinstance(
            value,
            str,
        )
        or not value.strip()
    ):
        raise ValueError(
            f"{field_name} must be a non-blank string."
        )

    return value


def _optional_string(
    value: object,
    *,
    field_name: str,
) -> str | None:
    """Parse an optional string."""

    if value is None:
        return None

    return _require_string(
        value,
        field_name=field_name,
    )


def _require_bool(
    value: object,
    *,
    field_name: str,
) -> bool:
    """Require a Boolean value."""

    if not isinstance(
        value,
        bool,
    ):
        raise ValueError(
            f"{field_name} must be a Boolean."
        )

    return value


def _optional_number(
    value: object,
    *,
    field_name: str,
) -> float | None:
    """Parse an optional numeric value."""

    if value is None:
        return None

    if (
        isinstance(
            value,
            bool,
        )
        or not isinstance(
            value,
            (
                int,
                float,
            ),
        )
    ):
        raise ValueError(
            f"{field_name} must be numeric or null."
        )

    return float(
        value
    )


def _optional_int(
    value: object,
    *,
    field_name: str,
) -> int | None:
    """Parse an optional integer."""

    if value is None:
        return None

    if (
        isinstance(
            value,
            bool,
        )
        or not isinstance(
            value,
            int,
        )
    ):
        raise ValueError(
            f"{field_name} must be an integer or null."
        )

    return value


def _parse_task_type(
    value: object,
    *,
    field_name: str,
) -> TaskType:
    """Parse a task type enum."""

    text = _require_string(
        value,
        field_name=field_name,
    )

    try:
        return TaskType(
            text
        )
    except ValueError as exc:
        raise ValueError(
            f"Unknown {field_name}: {text!r}."
        ) from exc


def _parse_condition(
    value: object,
    *,
    field_name: str,
) -> VariationCondition:
    """Parse a variation condition enum."""

    text = _require_string(
        value,
        field_name=field_name,
    )

    try:
        return VariationCondition(
            text
        )
    except ValueError as exc:
        raise ValueError(
            f"Unknown {field_name}: {text!r}."
        ) from exc


def _response_sha256(
    response_text: str,
) -> str:
    """Hash response text exactly as stored."""

    return hashlib.sha256(
        response_text.encode(
            "utf-8"
        )
    ).hexdigest()


def load_annotation_source(
    path: Path,
) -> AnnotationSourceRecord:
    """Load and validate one annotation-source artifact."""

    try:
        raw: object = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Invalid annotation-source JSON: {path}"
        ) from exc

    root = _require_mapping(
        raw,
        field_name="annotation source",
    )

    artifact_type = _require_string(
        _require_field(
            root,
            "artifact_type",
        ),
        field_name="artifact_type",
    )

    source_format_version = _require_string(
        _require_field(
            root,
            "annotation_source_format_version",
        ),
        field_name=(
            "annotation_source_format_version"
        ),
    )

    benchmark_claim_eligible = (
        _require_bool(
            _require_field(
                root,
                "benchmark_claim_eligible",
            ),
            field_name=(
                "benchmark_claim_eligible"
            ),
        )
    )

    request = _require_mapping(
        _require_field(
            root,
            "request",
        ),
        field_name="request",
    )

    result = _require_mapping(
        _require_field(
            root,
            "result",
        ),
        field_name="result",
    )

    run_id = _require_string(
        _require_field(
            request,
            "run_id",
        ),
        field_name="request.run_id",
    )

    request_id = _require_string(
        _require_field(
            request,
            "request_id",
        ),
        field_name="request.request_id",
    )

    family_id = _require_string(
        _require_field(
            request,
            "family_id",
        ),
        field_name="request.family_id",
    )

    task_type = _parse_task_type(
        _require_field(
            request,
            "task_type",
        ),
        field_name="request.task_type",
    )

    condition = _parse_condition(
        _require_field(
            request,
            "condition",
        ),
        field_name="request.condition",
    )

    prompt_sha256 = _require_string(
        _require_field(
            request,
            "prompt_sha256",
        ),
        field_name="request.prompt_sha256",
    )

    prompt_text = _require_string(
        _require_field(
            request,
            "prompt_text",
        ),
        field_name="request.prompt_text",
    )

    result_status = _require_string(
        _require_field(
            result,
            "status",
        ),
        field_name="result.status",
    )

    if result_status != "SUCCESS":
        raise ValueError(
            "Dashboard data requires a successful "
            f"model result; got {result_status!r} "
            f"in {path}."
        )

    bindings: tuple[
        tuple[
            str,
            object,
            object,
        ],
        ...,
    ] = (
        (
            "run_id",
            run_id,
            _require_field(
                result,
                "run_id",
            ),
        ),
        (
            "request_id",
            request_id,
            _require_field(
                result,
                "request_id",
            ),
        ),
        (
            "family_id",
            family_id,
            _require_field(
                result,
                "family_id",
            ),
        ),
        (
            "task_type",
            task_type.value,
            _require_field(
                result,
                "task_type",
            ),
        ),
        (
            "condition",
            condition.value,
            _require_field(
                result,
                "condition",
            ),
        ),
        (
            "prompt_sha256",
            prompt_sha256,
            _require_field(
                result,
                "prompt_sha256",
            ),
        ),
    )

    for (
        field_name,
        request_value,
        result_value,
    ) in bindings:
        if request_value != result_value:
            raise ValueError(
                "Request/result binding mismatch "
                f"for {field_name!r} in {path}."
            )

    response_text = _require_string(
        _require_field(
            result,
            "response_text",
        ),
        field_name="result.response_text",
    )

    provider = _require_string(
        _require_field(
            result,
            "provider",
        ),
        field_name="result.provider",
    )

    requested_model = _require_string(
        _require_field(
            result,
            "requested_model",
        ),
        field_name="result.requested_model",
    )

    returned_model = _optional_string(
        result.get(
            "returned_model"
        ),
        field_name="result.returned_model",
    )

    finish_reason = _optional_string(
        result.get(
            "finish_reason"
        ),
        field_name="result.finish_reason",
    )

    latency_seconds = _optional_number(
        result.get(
            "latency_seconds"
        ),
        field_name="result.latency_seconds",
    )

    usage_value = result.get(
        "usage"
    )

    if usage_value is None:
        usage: Mapping[
            str,
            object,
        ] = {}
    else:
        usage = _require_mapping(
            usage_value,
            field_name="result.usage",
        )

    input_tokens = _optional_int(
        usage.get(
            "input_tokens"
        ),
        field_name="result.usage.input_tokens",
    )

    output_tokens = _optional_int(
        usage.get(
            "output_tokens"
        ),
        field_name="result.usage.output_tokens",
    )

    total_tokens = _optional_int(
        usage.get(
            "total_tokens"
        ),
        field_name="result.usage.total_tokens",
    )

    return AnnotationSourceRecord(
        source_path=path,
        artifact_type=artifact_type,
        source_format_version=(
            source_format_version
        ),
        benchmark_claim_eligible=(
            benchmark_claim_eligible
        ),
        run_id=run_id,
        request_id=request_id,
        family_id=family_id,
        task_type=task_type,
        condition=condition,
        prompt_sha256=prompt_sha256,
        prompt_text=prompt_text,
        response_text=response_text,
        provider=provider,
        requested_model=requested_model,
        returned_model=returned_model,
        finish_reason=finish_reason,
        latency_seconds=latency_seconds,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
    )


def source_paths_from_analysis(
    analysis: PilotAnalysis,
    *,
    project_root: Path = Path("."),
) -> tuple[Path, ...]:
    """Resolve source artifacts referenced by annotations."""

    paths: list[
        Path
    ] = []

    for annotation in analysis.annotations:
        path = Path(
            annotation.source_artifact
        )

        if not path.is_absolute():
            path = (
                project_root
                / path
            )

        paths.append(
            path
        )

    return tuple(
        paths
    )


def build_dashboard_dataset(
    analysis: PilotAnalysis,
    sources: Sequence[
        AnnotationSourceRecord
    ],
) -> DashboardDataset:
    """Join scored analysis with prompts and model responses."""

    source_by_key: dict[
        tuple[
            str,
            VariationCondition,
        ],
        AnnotationSourceRecord,
    ] = {}

    for source in sources:
        key = (
            source.family_id,
            source.condition,
        )

        if key in source_by_key:
            raise ValueError(
                "Duplicate annotation source for "
                f"family {source.family_id!r}, "
                f"condition {source.condition.value!r}."
            )

        source_by_key[
            key
        ] = source

    annotation_by_key = {
        (
            annotation.family_id,
            annotation.condition,
        ): annotation
        for annotation in analysis.annotations
    }

    expected_keys = set(
        annotation_by_key
    )

    source_keys = set(
        source_by_key
    )

    if source_keys != expected_keys:
        missing = sorted(
            (
                family_id,
                condition.value,
            )
            for (
                family_id,
                condition,
            ) in (
                expected_keys
                - source_keys
            )
        )

        unexpected = sorted(
            (
                family_id,
                condition.value,
            )
            for (
                family_id,
                condition,
            ) in (
                source_keys
                - expected_keys
            )
        )

        raise ValueError(
            "Annotation-source set does not "
            "match scored annotations. "
            f"missing={missing}; "
            f"unexpected={unexpected}."
        )

    dashboard_families: list[
        DashboardFamily
    ] = []

    for family in analysis.families:
        responses: list[
            DashboardResponse
        ] = []

        for condition in EXPECTED_CONDITIONS:
            key = (
                family.family_id,
                condition,
            )

            annotation = annotation_by_key[
                key
            ]

            source = source_by_key[
                key
            ]

            if source.run_id != analysis.run_id:
                raise ValueError(
                    "Annotation source run_id does "
                    "not match the analysis run."
                )

            if (
                source.request_id
                != annotation.request_id
            ):
                raise ValueError(
                    "Annotation source request_id "
                    "does not match the scored "
                    "annotation."
                )

            if (
                source.task_type
                is not annotation.task_type
            ):
                raise ValueError(
                    "Annotation source task_type "
                    "does not match the scored "
                    "annotation."
                )

            if (
                source.benchmark_claim_eligible
                != analysis.benchmark_claim_eligible
            ):
                raise ValueError(
                    "Annotation source benchmark "
                    "claim eligibility does not "
                    "match the analysis."
                )

            response_sha256 = (
                _response_sha256(
                    source.response_text
                )
            )

            if (
                response_sha256
                != annotation.response_sha256
            ):
                raise ValueError(
                    "Model response hash does not "
                    "match the scored annotation "
                    f"for {family.family_id!r}, "
                    f"{condition.value!r}."
                )

            if (
                condition
                is VariationCondition.STANDARD
            ):
                standard_contrast = None
            else:
                standard_contrast = (
                    family.standard_contrasts[
                        condition
                    ]
                )

            responses.append(
                DashboardResponse(
                    request_id=(
                        annotation.request_id
                    ),
                    family_id=(
                        family.family_id
                    ),
                    task_type=(
                        family.task_type
                    ),
                    condition=condition,
                    prompt_text=(
                        source.prompt_text
                    ),
                    response_text=(
                        source.response_text
                    ),
                    response_outcome=(
                        family.response_outcomes[
                            condition
                        ]
                    ),
                    standard_contrast=(
                        standard_contrast
                    ),
                    response_sha256=(
                        response_sha256
                    ),
                    provider=source.provider,
                    requested_model=(
                        source.requested_model
                    ),
                    returned_model=(
                        source.returned_model
                    ),
                    finish_reason=(
                        source.finish_reason
                    ),
                    latency_seconds=(
                        source.latency_seconds
                    ),
                    input_tokens=(
                        source.input_tokens
                    ),
                    output_tokens=(
                        source.output_tokens
                    ),
                    total_tokens=(
                        source.total_tokens
                    ),
                )
            )

        dashboard_families.append(
            DashboardFamily(
                family_id=family.family_id,
                task_type=family.task_type,
                rubric_version=(
                    family.rubric_version
                ),
                family_outcome=(
                    family.family_outcome
                ),
                responses=tuple(
                    responses
                ),
            )
        )

    return DashboardDataset(
        format_version=(
            DASHBOARD_DATA_FORMAT_VERSION
        ),
        run_id=analysis.run_id,
        annotator_id=analysis.annotator_id,
        benchmark_claim_eligible=(
            analysis.benchmark_claim_eligible
        ),
        annotation_protocol_version=(
            analysis.annotation_protocol_version
        ),
        scoring_protocol_version=(
            analysis.scoring_protocol_version
        ),
        families=tuple(
            dashboard_families
        ),
    )


def load_dashboard_dataset(
    annotation_paths: Sequence[
        Path
    ],
    *,
    project_root: Path = Path("."),
) -> DashboardDataset:
    """Load scored annotations and their source responses."""

    analysis = analyze_annotation_paths(
        annotation_paths
    )

    source_paths = (
        source_paths_from_analysis(
            analysis,
            project_root=project_root,
        )
    )

    sources = tuple(
        load_annotation_source(
            path
        )
        for path in source_paths
    )

    return build_dashboard_dataset(
        analysis,
        sources,
    )


def dashboard_dataset_to_dict(
    dataset: DashboardDataset,
) -> dict[str, object]:
    """Serialize dashboard data for UI or API use."""

    family_payloads: list[
        dict[str, object]
    ] = []

    for family in dataset.families:
        response_payloads: list[
            dict[str, object]
        ] = []

        for response in family.responses:
            response_payloads.append(
                {
                    "request_id": (
                        response.request_id
                    ),
                    "condition": (
                        response.condition.value
                    ),
                    "prompt_text": (
                        response.prompt_text
                    ),
                    "response_text": (
                        response.response_text
                    ),
                    "response_outcome": (
                        response.response_outcome.value
                    ),
                    "standard_contrast": (
                        response.standard_contrast.value
                        if (
                            response.standard_contrast
                            is not None
                        )
                        else None
                    ),
                    "response_sha256": (
                        response.response_sha256
                    ),
                    "provider": (
                        response.provider
                    ),
                    "requested_model": (
                        response.requested_model
                    ),
                    "returned_model": (
                        response.returned_model
                    ),
                    "finish_reason": (
                        response.finish_reason
                    ),
                    "latency_seconds": (
                        response.latency_seconds
                    ),
                    "input_tokens": (
                        response.input_tokens
                    ),
                    "output_tokens": (
                        response.output_tokens
                    ),
                    "total_tokens": (
                        response.total_tokens
                    ),
                }
            )

        family_payloads.append(
            {
                "family_id": (
                    family.family_id
                ),
                "task_type": (
                    family.task_type.value
                ),
                "rubric_version": (
                    family.rubric_version
                ),
                "family_outcome": (
                    family.family_outcome.value
                ),
                "responses": (
                    response_payloads
                ),
            }
        )

    return {
        "dashboard_data_format_version": (
            dataset.format_version
        ),
        "run_id": dataset.run_id,
        "annotator_id": (
            dataset.annotator_id
        ),
        "benchmark_claim_eligible": (
            dataset.benchmark_claim_eligible
        ),
        "annotation_protocol_version": (
            dataset.annotation_protocol_version
        ),
        "scoring_protocol_version": (
            dataset.scoring_protocol_version
        ),
        "family_count": len(
            dataset.families
        ),
        "response_count": sum(
            len(
                family.responses
            )
            for family in dataset.families
        ),
        "families": family_payloads,
    }