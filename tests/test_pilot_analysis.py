import json
from collections.abc import Mapping
from pathlib import Path

import pytest

from sociolinguistic_invariance.annotation_workflow import (
    HUMAN_SCORED_RESPONSE_ARTIFACT_FORMAT_VERSION,
    HUMAN_SCORED_RESPONSE_ARTIFACT_TYPE,
)
from sociolinguistic_invariance.core import (
    TaskType,
    VariationCondition,
)
from sociolinguistic_invariance.pilot_analysis import (
    AnnotationRecord,
    analyze_annotation_paths,
    build_pilot_analysis,
    load_annotation_artifact,
    pilot_analysis_to_dict,
)
from sociolinguistic_invariance.scoring import (
    FamilyOutcome,
    ResponseOutcome,
    StandardContrastOutcome,
)

ANNOTATION_PROTOCOL_VERSION = (
    "annotation-protocol-v0.1"
)

SCORING_PROTOCOL_VERSION = (
    "scoring-protocol-v0.1"
)


def _record(
    *,
    family_id: str = "FP_0001",
    task_type: TaskType = (
        TaskType.FALSE_PREMISE_CORRECTION
    ),
    condition: VariationCondition = (
        VariationCondition.STANDARD
    ),
    outcome: ResponseOutcome = (
        ResponseOutcome.PASS
    ),
    run_id: str = "run_test",
    annotator_id: str = "annotator-001",
    benchmark_claim_eligible: bool = False,
    rubric_version: str = (
        "false-premise-correction-rubric-v0.1"
    ),
) -> AnnotationRecord:
    return AnnotationRecord(
        annotation_artifact=(
            "results/annotations/"
            f"{family_id}_{condition.value}.json"
        ),
        source_artifact=(
            "results/annotation_sources/"
            f"{family_id}_{condition.value}.json"
        ),
        source_artifact_type=(
            "single_response_annotation_source"
        ),
        run_id=run_id,
        request_id=(
            f"request_{family_id}_"
            f"{condition.value}"
        ),
        family_id=family_id,
        task_type=task_type,
        condition=condition,
        response_sha256="a" * 64,
        annotator_id=annotator_id,
        annotation_protocol_version=(
            ANNOTATION_PROTOCOL_VERSION
        ),
        rubric_version=rubric_version,
        scoring_protocol_version=(
            SCORING_PROTOCOL_VERSION
        ),
        outcome=outcome,
        benchmark_claim_eligible=(
            benchmark_claim_eligible
        ),
    )


def _complete_family(
    *,
    family_id: str,
    task_type: TaskType,
    rubric_version: str,
    outcomes: Mapping[
        VariationCondition,
        ResponseOutcome,
    ],
) -> tuple[
    AnnotationRecord,
    ...,
]:
    return tuple(
        _record(
            family_id=family_id,
            task_type=task_type,
            condition=condition,
            outcome=outcomes[
                condition
            ],
            rubric_version=(
                rubric_version
            ),
        )
        for condition in (
            VariationCondition.STANDARD,
            VariationCondition.FORMAL,
            VariationCondition.INFORMAL,
            VariationCondition.GREEKLISH,
        )
    )


def _passing_outcomes(
) -> dict[
    VariationCondition,
    ResponseOutcome,
]:
    return {
        VariationCondition.STANDARD: (
            ResponseOutcome.PASS
        ),
        VariationCondition.FORMAL: (
            ResponseOutcome.PASS
        ),
        VariationCondition.INFORMAL: (
            ResponseOutcome.PASS
        ),
        VariationCondition.GREEKLISH: (
            ResponseOutcome.PASS
        ),
    }


def _disparity_outcomes(
) -> dict[
    VariationCondition,
    ResponseOutcome,
]:
    return {
        VariationCondition.STANDARD: (
            ResponseOutcome.PASS
        ),
        VariationCondition.FORMAL: (
            ResponseOutcome.PASS
        ),
        VariationCondition.INFORMAL: (
            ResponseOutcome.PASS
        ),
        VariationCondition.GREEKLISH: (
            ResponseOutcome.FAIL
        ),
    }


def _artifact_payload(
    *,
    task_type: TaskType = (
        TaskType.FALSE_PREMISE_CORRECTION
    ),
    condition: VariationCondition = (
        VariationCondition.STANDARD
    ),
    outcome: ResponseOutcome = (
        ResponseOutcome.PASS
    ),
    source_claim_eligible: bool = False,
    claim_eligible: bool = False,
) -> dict[str, object]:
    return {
        "artifact_type": (
            HUMAN_SCORED_RESPONSE_ARTIFACT_TYPE
        ),
        "artifact_format_version": (
            HUMAN_SCORED_RESPONSE_ARTIFACT_FORMAT_VERSION
        ),
        "source_artifact": (
            "results/annotation_sources/"
            "source.json"
        ),
        "source_artifact_type": (
            "single_response_annotation_source"
        ),
        "source_benchmark_claim_eligible": (
            source_claim_eligible
        ),
        "benchmark_claim_eligible": (
            claim_eligible
        ),
        "scored_annotation": {
            "annotation": {
                "annotation_protocol_version": (
                    ANNOTATION_PROTOCOL_VERSION
                ),
                "rubric_version": (
                    "false-premise-correction-"
                    "rubric-v0.1"
                ),
                "run_id": "run_test",
                "request_id": "request_test",
                "family_id": "FP_0001",
                "task_type": (
                    task_type.value
                ),
                "condition": (
                    condition.value
                ),
                "response_sha256": (
                    "a" * 64
                ),
                "annotator_id": (
                    "annotator-001"
                ),
            },
            "response_score": {
                "task_type": (
                    task_type.value
                ),
                "outcome": (
                    outcome.value
                ),
                "scoring_protocol_version": (
                    SCORING_PROTOCOL_VERSION
                ),
            },
        },
    }


def test_load_annotation_artifact_parses_record(
    tmp_path: Path,
) -> None:
    path = (
        tmp_path
        / "annotation.json"
    )

    path.write_text(
        json.dumps(
            _artifact_payload()
        ),
        encoding="utf-8",
    )

    record = load_annotation_artifact(
        path
    )

    assert record.run_id == "run_test"
    assert record.family_id == "FP_0001"
    assert (
        record.task_type
        is TaskType.FALSE_PREMISE_CORRECTION
    )
    assert (
        record.condition
        is VariationCondition.STANDARD
    )
    assert (
        record.outcome
        is ResponseOutcome.PASS
    )
    assert (
        record.benchmark_claim_eligible
        is False
    )


def test_load_rejects_wrong_artifact_type(
    tmp_path: Path,
) -> None:
    path = (
        tmp_path
        / "annotation.json"
    )

    payload = _artifact_payload()
    payload[
        "artifact_type"
    ] = "wrong_type"

    path.write_text(
        json.dumps(
            payload
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="artifact_type",
    ):
        load_annotation_artifact(
            path
        )


def test_load_rejects_claim_eligibility_mismatch(
    tmp_path: Path,
) -> None:
    path = (
        tmp_path
        / "annotation.json"
    )

    path.write_text(
        json.dumps(
            _artifact_payload(
                source_claim_eligible=False,
                claim_eligible=True,
            )
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match=(
            "source_benchmark_claim_eligible"
        ),
    ):
        load_annotation_artifact(
            path
        )


def test_load_rejects_score_task_type_mismatch(
    tmp_path: Path,
) -> None:
    path = (
        tmp_path
        / "annotation.json"
    )

    payload = _artifact_payload()

    scored = payload[
        "scored_annotation"
    ]

    assert isinstance(
        scored,
        dict,
    )

    response_score = scored[
        "response_score"
    ]

    assert isinstance(
        response_score,
        dict,
    )

    response_score[
        "task_type"
    ] = TaskType.BENIGN_REQUEST.value

    path.write_text(
        json.dumps(
            payload
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="must agree",
    ):
        load_annotation_artifact(
            path
        )


def test_build_derives_disparity_and_contrasts(
) -> None:
    records = _complete_family(
        family_id="FP_0001",
        task_type=(
            TaskType.FALSE_PREMISE_CORRECTION
        ),
        rubric_version=(
            "false-premise-correction-rubric-v0.1"
        ),
        outcomes=_disparity_outcomes(),
    )

    analysis = build_pilot_analysis(
        records
    )

    assert len(
        analysis.families
    ) == 1

    family = analysis.families[
        0
    ]

    assert (
        family.family_outcome
        is FamilyOutcome.DISPARITY
    )

    assert (
        family.standard_contrasts[
            VariationCondition.FORMAL
        ]
        is StandardContrastOutcome.STABLE_SUCCESS
    )

    assert (
        family.standard_contrasts[
            VariationCondition.INFORMAL
        ]
        is StandardContrastOutcome.STABLE_SUCCESS
    )

    assert (
        family.standard_contrasts[
            VariationCondition.GREEKLISH
        ]
        is StandardContrastOutcome.DEGRADATION
    )


def test_build_derives_robust_success(
) -> None:
    records = _complete_family(
        family_id="BR_0001",
        task_type=(
            TaskType.BENIGN_REQUEST
        ),
        rubric_version=(
            "benign-request-rubric-v0.1"
        ),
        outcomes=_passing_outcomes(),
    )

    analysis = build_pilot_analysis(
        records
    )

    family = analysis.families[
        0
    ]

    assert (
        family.family_outcome
        is FamilyOutcome.ROBUST_SUCCESS
    )

    assert all(
        contrast
        is StandardContrastOutcome.STABLE_SUCCESS
        for contrast
        in family.standard_contrasts.values()
    )


def test_build_rejects_duplicate_family_condition(
) -> None:
    records = _complete_family(
        family_id="FP_0001",
        task_type=(
            TaskType.FALSE_PREMISE_CORRECTION
        ),
        rubric_version=(
            "false-premise-correction-rubric-v0.1"
        ),
        outcomes=_passing_outcomes(),
    )

    duplicate_records = (
        *records,
        records[
            0
        ],
    )

    with pytest.raises(
        ValueError,
        match="Duplicate annotation",
    ):
        build_pilot_analysis(
            duplicate_records
        )


def test_build_rejects_missing_condition(
) -> None:
    records = _complete_family(
        family_id="FP_0001",
        task_type=(
            TaskType.FALSE_PREMISE_CORRECTION
        ),
        rubric_version=(
            "false-premise-correction-rubric-v0.1"
        ),
        outcomes=_passing_outcomes(),
    )

    incomplete = records[
        :-1
    ]

    with pytest.raises(
        ValueError,
        match="missing=greeklish",
    ):
        build_pilot_analysis(
            incomplete
        )


def test_build_rejects_multiple_runs(
) -> None:
    records = list(
        _complete_family(
            family_id="FP_0001",
            task_type=(
                TaskType.FALSE_PREMISE_CORRECTION
            ),
            rubric_version=(
                "false-premise-correction-"
                "rubric-v0.1"
            ),
            outcomes=_passing_outcomes(),
        )
    )

    records[
        0
    ] = _record(
        family_id="FP_0001",
        task_type=(
            TaskType.FALSE_PREMISE_CORRECTION
        ),
        condition=(
            VariationCondition.STANDARD
        ),
        outcome=(
            ResponseOutcome.PASS
        ),
        run_id="different_run",
    )

    with pytest.raises(
        ValueError,
        match="exactly one run",
    ):
        build_pilot_analysis(
            records
        )


def test_build_rejects_multiple_annotators(
) -> None:
    records = list(
        _complete_family(
            family_id="FP_0001",
            task_type=(
                TaskType.FALSE_PREMISE_CORRECTION
            ),
            rubric_version=(
                "false-premise-correction-"
                "rubric-v0.1"
            ),
            outcomes=_passing_outcomes(),
        )
    )

    records[
        0
    ] = _record(
        family_id="FP_0001",
        task_type=(
            TaskType.FALSE_PREMISE_CORRECTION
        ),
        condition=(
            VariationCondition.STANDARD
        ),
        outcome=(
            ResponseOutcome.PASS
        ),
        annotator_id="annotator-002",
    )

    with pytest.raises(
        ValueError,
        match="exactly one annotator",
    ):
        build_pilot_analysis(
            records
        )


def test_build_rejects_mixed_claim_eligibility(
) -> None:
    records = list(
        _complete_family(
            family_id="FP_0001",
            task_type=(
                TaskType.FALSE_PREMISE_CORRECTION
            ),
            rubric_version=(
                "false-premise-correction-"
                "rubric-v0.1"
            ),
            outcomes=_passing_outcomes(),
        )
    )

    records[
        0
    ] = _record(
        family_id="FP_0001",
        task_type=(
            TaskType.FALSE_PREMISE_CORRECTION
        ),
        condition=(
            VariationCondition.STANDARD
        ),
        outcome=(
            ResponseOutcome.PASS
        ),
        benchmark_claim_eligible=True,
    )

    with pytest.raises(
        ValueError,
        match="claim eligibility",
    ):
        build_pilot_analysis(
            records
        )


def test_analysis_to_dict_reports_counts_and_ordering(
) -> None:
    fp_records = _complete_family(
        family_id="FP_0001",
        task_type=(
            TaskType.FALSE_PREMISE_CORRECTION
        ),
        rubric_version=(
            "false-premise-correction-rubric-v0.1"
        ),
        outcomes=_disparity_outcomes(),
    )

    eu_records = _complete_family(
        family_id="EU_0001",
        task_type=(
            TaskType.EPISTEMIC_UNCERTAINTY
        ),
        rubric_version=(
            "epistemic-uncertainty-rubric-v0.1"
        ),
        outcomes=_disparity_outcomes(),
    )

    br_records = _complete_family(
        family_id="BR_0001",
        task_type=(
            TaskType.BENIGN_REQUEST
        ),
        rubric_version=(
            "benign-request-rubric-v0.1"
        ),
        outcomes=_passing_outcomes(),
    )

    analysis = build_pilot_analysis(
        (
            *br_records,
            *eu_records,
            *fp_records,
        )
    )

    payload = pilot_analysis_to_dict(
        analysis
    )

    assert payload[
        "response_count"
    ] == 12

    assert payload[
        "family_count"
    ] == 3

    assert payload[
        "benchmark_claim_eligible"
    ] is False

    response_counts = payload[
        "response_outcome_counts"
    ]

    assert isinstance(
        response_counts,
        dict,
    )

    assert response_counts[
        "PASS"
    ] == 10

    assert response_counts[
        "FAIL"
    ] == 2

    assert response_counts[
        "UNCLEAR"
    ] == 0

    family_counts = payload[
        "family_outcome_counts"
    ]

    assert isinstance(
        family_counts,
        dict,
    )

    assert family_counts[
        "DISPARITY"
    ] == 2

    assert family_counts[
        "ROBUST_SUCCESS"
    ] == 1

    contrast_counts = payload[
        "standard_contrast_counts"
    ]

    assert isinstance(
        contrast_counts,
        dict,
    )

    assert contrast_counts[
        "STABLE_SUCCESS"
    ] == 7

    assert contrast_counts[
        "DEGRADATION"
    ] == 2

    families = payload[
        "families"
    ]

    assert isinstance(
        families,
        list,
    )

    assert [
        family[
            "family_id"
        ]
        for family in families
        if isinstance(
            family,
            dict,
        )
    ] == [
        "FP_0001",
        "EU_0001",
        "BR_0001",
    ]


def test_analyze_annotation_paths_loads_files(
    tmp_path: Path,
) -> None:
    paths: list[
        Path
    ] = []

    for condition in (
        VariationCondition.STANDARD,
        VariationCondition.FORMAL,
        VariationCondition.INFORMAL,
        VariationCondition.GREEKLISH,
    ):
        path = (
            tmp_path
            / f"{condition.value}.json"
        )

        path.write_text(
            json.dumps(
                _artifact_payload(
                    condition=condition,
                )
            ),
            encoding="utf-8",
        )

        paths.append(
            path
        )

    analysis = analyze_annotation_paths(
        paths
    )

    assert len(
        analysis.annotations
    ) == 4

    assert len(
        analysis.families
    ) == 1

    assert (
        analysis.families[
            0
        ].family_outcome
        is FamilyOutcome.ROBUST_SUCCESS
    )