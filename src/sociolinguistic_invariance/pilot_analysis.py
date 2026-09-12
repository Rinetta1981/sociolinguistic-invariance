from __future__ import annotations

import json
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, cast

from sociolinguistic_invariance.annotation_workflow import (
    HUMAN_SCORED_RESPONSE_ARTIFACT_FORMAT_VERSION,
    HUMAN_SCORED_RESPONSE_ARTIFACT_TYPE,
)
from sociolinguistic_invariance.core import (
    TaskType,
    VariationCondition,
)
from sociolinguistic_invariance.scoring import (
    FamilyOutcome,
    ResponseOutcome,
    StandardContrastOutcome,
    derive_family_outcome,
    derive_standard_contrast,
)

PILOT_ANALYSIS_FORMAT_VERSION: Final = (
    "pilot-analysis-v0.1"
)

EXPECTED_CONDITIONS: Final[
    tuple[VariationCondition, ...]
] = (
    VariationCondition.STANDARD,
    VariationCondition.FORMAL,
    VariationCondition.INFORMAL,
    VariationCondition.GREEKLISH,
)

COMPARISON_CONDITIONS: Final[
    tuple[VariationCondition, ...]
] = (
    VariationCondition.FORMAL,
    VariationCondition.INFORMAL,
    VariationCondition.GREEKLISH,
)

_TASK_ORDER: Final[
    dict[TaskType, int]
] = {
    TaskType.FALSE_PREMISE_CORRECTION: 0,
    TaskType.EPISTEMIC_UNCERTAINTY: 1,
    TaskType.BENIGN_REQUEST: 2,
}

_CONDITION_ORDER: Final[
    dict[VariationCondition, int]
] = {
    condition: index
    for index, condition in enumerate(
        EXPECTED_CONDITIONS
    )
}


@dataclass(
    frozen=True,
    slots=True,
)
class AnnotationRecord:
    """Normalized information from one annotation artifact."""

    annotation_artifact: str
    source_artifact: str
    source_artifact_type: str
    run_id: str
    request_id: str
    family_id: str
    task_type: TaskType
    condition: VariationCondition
    response_sha256: str
    annotator_id: str
    annotation_protocol_version: str
    rubric_version: str
    scoring_protocol_version: str
    outcome: ResponseOutcome
    benchmark_claim_eligible: bool


@dataclass(
    frozen=True,
    slots=True,
)
class FamilyAnalysis:
    """Deterministic analysis for one semantic family."""

    family_id: str
    task_type: TaskType
    rubric_version: str
    response_outcomes: Mapping[
        VariationCondition,
        ResponseOutcome,
    ]
    family_outcome: FamilyOutcome
    standard_contrasts: Mapping[
        VariationCondition,
        StandardContrastOutcome,
    ]


@dataclass(
    frozen=True,
    slots=True,
)
class PilotAnalysis:
    """Aggregated analysis of one fully annotated run."""

    run_id: str
    annotator_id: str
    annotation_protocol_version: str
    scoring_protocol_version: str
    benchmark_claim_eligible: bool
    annotations: tuple[
        AnnotationRecord,
        ...,
    ]
    families: tuple[
        FamilyAnalysis,
        ...,
    ]


def _require_mapping(
    value: object,
    *,
    field_name: str,
) -> Mapping[str, object]:
    """Require one JSON object."""

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
    """Require one object field."""

    if field_name not in record:
        raise ValueError(
            f"Missing required field: {field_name}."
        )

    return record[field_name]


def _require_non_blank_string(
    value: object,
    *,
    field_name: str,
) -> str:
    """Require one non-blank string."""

    if (
        not isinstance(
            value,
            str,
        )
        or not value.strip()
    ):
        raise ValueError(
            f"{field_name} must be non-blank."
        )

    return value


def _require_bool(
    value: object,
    *,
    field_name: str,
) -> bool:
    """Require one Boolean."""

    if not isinstance(
        value,
        bool,
    ):
        raise ValueError(
            f"{field_name} must be a Boolean."
        )

    return value


def _require_expected_string(
    value: object,
    *,
    field_name: str,
    expected: str,
) -> str:
    """Require one exact string value."""

    observed = _require_non_blank_string(
        value,
        field_name=field_name,
    )

    if observed != expected:
        raise ValueError(
            f"{field_name} must be "
            f"{expected!r}; got {observed!r}."
        )

    return observed


def _parse_task_type(
    value: object,
    *,
    field_name: str,
) -> TaskType:
    """Parse one task type."""

    text = _require_non_blank_string(
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
    """Parse one variation condition."""

    text = _require_non_blank_string(
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


def _parse_response_outcome(
    value: object,
    *,
    field_name: str,
) -> ResponseOutcome:
    """Parse one deterministic response outcome."""

    text = _require_non_blank_string(
        value,
        field_name=field_name,
    )

    try:
        return ResponseOutcome(
            text
        )
    except ValueError as exc:
        raise ValueError(
            f"Unknown {field_name}: {text!r}."
        ) from exc


def load_annotation_artifact(
    path: Path,
) -> AnnotationRecord:
    """Load and normalize one annotation artifact."""

    try:
        raw: object = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Invalid JSON annotation artifact: "
            f"{path}"
        ) from exc

    root = _require_mapping(
        raw,
        field_name="annotation artifact",
    )

    _require_expected_string(
        _require_field(
            root,
            "artifact_type",
        ),
        field_name="artifact_type",
        expected=(
            HUMAN_SCORED_RESPONSE_ARTIFACT_TYPE
        ),
    )

    _require_expected_string(
        _require_field(
            root,
            "artifact_format_version",
        ),
        field_name="artifact_format_version",
        expected=(
            HUMAN_SCORED_RESPONSE_ARTIFACT_FORMAT_VERSION
        ),
    )

    source_artifact = (
        _require_non_blank_string(
            _require_field(
                root,
                "source_artifact",
            ),
            field_name="source_artifact",
        )
    )

    source_artifact_type = (
        _require_non_blank_string(
            _require_field(
                root,
                "source_artifact_type",
            ),
            field_name="source_artifact_type",
        )
    )

    source_claim_eligible = (
        _require_bool(
            _require_field(
                root,
                "source_benchmark_claim_eligible",
            ),
            field_name=(
                "source_benchmark_claim_eligible"
            ),
        )
    )

    claim_eligible = _require_bool(
        _require_field(
            root,
            "benchmark_claim_eligible",
        ),
        field_name="benchmark_claim_eligible",
    )

    if (
        source_claim_eligible
        != claim_eligible
    ):
        raise ValueError(
            "source_benchmark_claim_eligible "
            "and benchmark_claim_eligible "
            "must agree."
        )

    scored_annotation = (
        _require_mapping(
            _require_field(
                root,
                "scored_annotation",
            ),
            field_name="scored_annotation",
        )
    )

    annotation = _require_mapping(
        _require_field(
            scored_annotation,
            "annotation",
        ),
        field_name=(
            "scored_annotation.annotation"
        ),
    )

    response_score = _require_mapping(
        _require_field(
            scored_annotation,
            "response_score",
        ),
        field_name=(
            "scored_annotation.response_score"
        ),
    )

    annotation_protocol_version = (
        _require_non_blank_string(
            _require_field(
                annotation,
                "annotation_protocol_version",
            ),
            field_name=(
                "annotation_protocol_version"
            ),
        )
    )

    rubric_version = (
        _require_non_blank_string(
            _require_field(
                annotation,
                "rubric_version",
            ),
            field_name="rubric_version",
        )
    )

    run_id = _require_non_blank_string(
        _require_field(
            annotation,
            "run_id",
        ),
        field_name="run_id",
    )

    request_id = _require_non_blank_string(
        _require_field(
            annotation,
            "request_id",
        ),
        field_name="request_id",
    )

    family_id = _require_non_blank_string(
        _require_field(
            annotation,
            "family_id",
        ),
        field_name="family_id",
    )

    task_type = _parse_task_type(
        _require_field(
            annotation,
            "task_type",
        ),
        field_name="task_type",
    )

    condition = _parse_condition(
        _require_field(
            annotation,
            "condition",
        ),
        field_name="condition",
    )

    response_sha256 = (
        _require_non_blank_string(
            _require_field(
                annotation,
                "response_sha256",
            ),
            field_name="response_sha256",
        )
    )

    annotator_id = (
        _require_non_blank_string(
            _require_field(
                annotation,
                "annotator_id",
            ),
            field_name="annotator_id",
        )
    )

    score_task_type = _parse_task_type(
        _require_field(
            response_score,
            "task_type",
        ),
        field_name=(
            "response_score.task_type"
        ),
    )

    if score_task_type is not task_type:
        raise ValueError(
            "Annotation task_type and "
            "response_score.task_type "
            "must agree."
        )

    scoring_protocol_version = (
        _require_non_blank_string(
            _require_field(
                response_score,
                "scoring_protocol_version",
            ),
            field_name=(
                "scoring_protocol_version"
            ),
        )
    )

    outcome = _parse_response_outcome(
        _require_field(
            response_score,
            "outcome",
        ),
        field_name="response_score.outcome",
    )

    return AnnotationRecord(
        annotation_artifact=str(
            path
        ),
        source_artifact=source_artifact,
        source_artifact_type=(
            source_artifact_type
        ),
        run_id=run_id,
        request_id=request_id,
        family_id=family_id,
        task_type=task_type,
        condition=condition,
        response_sha256=response_sha256,
        annotator_id=annotator_id,
        annotation_protocol_version=(
            annotation_protocol_version
        ),
        rubric_version=rubric_version,
        scoring_protocol_version=(
            scoring_protocol_version
        ),
        outcome=outcome,
        benchmark_claim_eligible=(
            claim_eligible
        ),
    )


def _record_sort_key(
    record: AnnotationRecord,
) -> tuple[
    int,
    str,
    int,
    str,
]:
    """Return a deterministic response sort key."""

    return (
        _TASK_ORDER.get(
            record.task_type,
            len(
                _TASK_ORDER
            ),
        ),
        record.family_id,
        _CONDITION_ORDER[
            record.condition
        ],
        record.request_id,
    )


def _family_sort_key(
    family: FamilyAnalysis,
) -> tuple[
    int,
    str,
]:
    """Return a deterministic family sort key."""

    return (
        _TASK_ORDER.get(
            family.task_type,
            len(
                _TASK_ORDER
            ),
        ),
        family.family_id,
    )


def build_pilot_analysis(
    records: Sequence[
        AnnotationRecord
    ],
) -> PilotAnalysis:
    """Build a validated deterministic run analysis."""

    if not records:
        raise ValueError(
            "At least one annotation record "
            "is required."
        )

    run_ids = {
        record.run_id
        for record in records
    }

    if len(
        run_ids
    ) != 1:
        raise ValueError(
            "All annotation records must "
            "belong to exactly one run."
        )

    annotator_ids = {
        record.annotator_id
        for record in records
    }

    if len(
        annotator_ids
    ) != 1:
        raise ValueError(
            "All annotation records must "
            "belong to exactly one annotator."
        )

    annotation_protocol_versions = {
        record.annotation_protocol_version
        for record in records
    }

    if len(
        annotation_protocol_versions
    ) != 1:
        raise ValueError(
            "All annotation records must use "
            "one annotation protocol version."
        )

    scoring_protocol_versions = {
        record.scoring_protocol_version
        for record in records
    }

    if len(
        scoring_protocol_versions
    ) != 1:
        raise ValueError(
            "All annotation records must use "
            "one scoring protocol version."
        )

    claim_eligibility_values = {
        record.benchmark_claim_eligible
        for record in records
    }

    if len(
        claim_eligibility_values
    ) != 1:
        raise ValueError(
            "All annotation records in one run "
            "must have the same benchmark "
            "claim eligibility."
        )

    seen_family_conditions: set[
        tuple[
            str,
            VariationCondition,
        ]
    ] = set()

    records_by_family: dict[
        str,
        list[
            AnnotationRecord
        ],
    ] = {}

    for record in records:
        key = (
            record.family_id,
            record.condition,
        )

        if key in seen_family_conditions:
            raise ValueError(
                "Duplicate annotation for "
                f"family {record.family_id!r}, "
                f"condition "
                f"{record.condition.value!r}."
            )

        seen_family_conditions.add(
            key
        )

        records_by_family.setdefault(
            record.family_id,
            [],
        ).append(
            record
        )

    expected_condition_set = set(
        EXPECTED_CONDITIONS
    )

    family_analyses: list[
        FamilyAnalysis
    ] = []

    for (
        family_id,
        family_records,
    ) in records_by_family.items():
        task_types = {
            record.task_type
            for record in family_records
        }

        if len(
            task_types
        ) != 1:
            raise ValueError(
                f"Family {family_id!r} "
                "contains multiple task types."
            )

        rubric_versions = {
            record.rubric_version
            for record in family_records
        }

        if len(
            rubric_versions
        ) != 1:
            raise ValueError(
                f"Family {family_id!r} "
                "contains multiple rubric "
                "versions."
            )

        response_outcomes = {
            record.condition: record.outcome
            for record in family_records
        }

        actual_condition_set = set(
            response_outcomes
        )

        if (
            actual_condition_set
            != expected_condition_set
        ):
            missing = [
                condition.value
                for condition
                in EXPECTED_CONDITIONS
                if condition
                not in actual_condition_set
            ]

            unexpected = sorted(
                condition.value
                for condition
                in actual_condition_set
                if condition
                not in expected_condition_set
            )

            details: list[
                str
            ] = []

            if missing:
                details.append(
                    "missing="
                    + ",".join(
                        missing
                    )
                )

            if unexpected:
                details.append(
                    "unexpected="
                    + ",".join(
                        unexpected
                    )
                )

            detail_text = "; ".join(
                details
            )

            raise ValueError(
                f"Family {family_id!r} must "
                "contain exactly the four "
                "required conditions"
                + (
                    f": {detail_text}."
                    if detail_text
                    else "."
                )
            )

        ordered_response_outcomes = {
            condition: response_outcomes[
                condition
            ]
            for condition
            in EXPECTED_CONDITIONS
        }

        family_outcome = (
            derive_family_outcome(
                ordered_response_outcomes
            )
        )

        standard_outcome = (
            ordered_response_outcomes[
                VariationCondition.STANDARD
            ]
        )

        standard_contrasts = {
            condition: (
                derive_standard_contrast(
                    standard_outcome,
                    ordered_response_outcomes[
                        condition
                    ],
                )
            )
            for condition
            in COMPARISON_CONDITIONS
        }

        task_type = next(
            iter(
                task_types
            )
        )

        rubric_version = next(
            iter(
                rubric_versions
            )
        )

        family_analyses.append(
            FamilyAnalysis(
                family_id=family_id,
                task_type=task_type,
                rubric_version=(
                    rubric_version
                ),
                response_outcomes=(
                    ordered_response_outcomes
                ),
                family_outcome=(
                    family_outcome
                ),
                standard_contrasts=(
                    standard_contrasts
                ),
            )
        )

    ordered_records = tuple(
        sorted(
            records,
            key=_record_sort_key,
        )
    )

    ordered_families = tuple(
        sorted(
            family_analyses,
            key=_family_sort_key,
        )
    )

    return PilotAnalysis(
        run_id=next(
            iter(
                run_ids
            )
        ),
        annotator_id=next(
            iter(
                annotator_ids
            )
        ),
        annotation_protocol_version=next(
            iter(
                annotation_protocol_versions
            )
        ),
        scoring_protocol_version=next(
            iter(
                scoring_protocol_versions
            )
        ),
        benchmark_claim_eligible=next(
            iter(
                claim_eligibility_values
            )
        ),
        annotations=ordered_records,
        families=ordered_families,
    )


def analyze_annotation_paths(
    paths: Sequence[
        Path
    ],
) -> PilotAnalysis:
    """Load annotation files and analyze them."""

    records = tuple(
        load_annotation_artifact(
            path
        )
        for path in paths
    )

    return build_pilot_analysis(
        records
    )


def pilot_analysis_to_dict(
    analysis: PilotAnalysis,
) -> dict[str, object]:
    """Serialize one pilot analysis deterministically."""

    response_counts = Counter(
        record.outcome
        for record in analysis.annotations
    )

    family_counts = Counter(
        family.family_outcome
        for family in analysis.families
    )

    contrast_counts = Counter(
        contrast
        for family in analysis.families
        for contrast
        in family.standard_contrasts.values()
    )

    response_count_payload: dict[
        str,
        int,
    ] = {
        outcome.value: response_counts[
            outcome
        ]
        for outcome in ResponseOutcome
    }

    family_count_payload: dict[
        str,
        int,
    ] = {
        outcome.value: family_counts[
            outcome
        ]
        for outcome in FamilyOutcome
    }

    contrast_count_payload: dict[
        str,
        int,
    ] = {
        outcome.value: contrast_counts[
            outcome
        ]
        for outcome
        in StandardContrastOutcome
    }

    family_payloads: list[
        dict[str, object]
    ] = []

    for family in analysis.families:
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
                "response_outcomes": {
                    condition.value: (
                        family.response_outcomes[
                            condition
                        ].value
                    )
                    for condition
                    in EXPECTED_CONDITIONS
                },
                "family_outcome": (
                    family.family_outcome.value
                ),
                (
                    "standard_referenced_contrasts"
                ): {
                    condition.value: (
                        family.standard_contrasts[
                            condition
                        ].value
                    )
                    for condition
                    in COMPARISON_CONDITIONS
                },
            }
        )

    response_payloads: list[
        dict[str, object]
    ] = []

    for record in analysis.annotations:
        response_payloads.append(
            {
                "annotation_artifact": (
                    record.annotation_artifact
                ),
                "source_artifact": (
                    record.source_artifact
                ),
                "source_artifact_type": (
                    record.source_artifact_type
                ),
                "request_id": (
                    record.request_id
                ),
                "family_id": (
                    record.family_id
                ),
                "task_type": (
                    record.task_type.value
                ),
                "condition": (
                    record.condition.value
                ),
                "response_sha256": (
                    record.response_sha256
                ),
                "rubric_version": (
                    record.rubric_version
                ),
                "outcome": (
                    record.outcome.value
                ),
            }
        )

    payload: dict[
        str,
        object,
    ] = {
        "analysis_format_version": (
            PILOT_ANALYSIS_FORMAT_VERSION
        ),
        "run_id": analysis.run_id,
        "annotator_id": (
            analysis.annotator_id
        ),
        "annotation_protocol_version": (
            analysis.annotation_protocol_version
        ),
        "scoring_protocol_version": (
            analysis.scoring_protocol_version
        ),
        "benchmark_claim_eligible": (
            analysis.benchmark_claim_eligible
        ),
        "response_count": len(
            analysis.annotations
        ),
        "family_count": len(
            analysis.families
        ),
        "response_outcome_counts": (
            response_count_payload
        ),
        "family_outcome_counts": (
            family_count_payload
        ),
        "standard_contrast_counts": (
            contrast_count_payload
        ),
        "families": family_payloads,
        "responses": response_payloads,
    }

    return payload