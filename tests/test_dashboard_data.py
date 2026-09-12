import hashlib
import json
from pathlib import Path

import pytest

from sociolinguistic_invariance.core import (
    TaskType,
    VariationCondition,
)
from sociolinguistic_invariance.dashboard_data import (
    DASHBOARD_DATA_FORMAT_VERSION,
    build_dashboard_dataset,
    dashboard_dataset_to_dict,
    load_annotation_source,
)
from sociolinguistic_invariance.pilot_analysis import (
    AnnotationRecord,
    FamilyAnalysis,
    PilotAnalysis,
)
from sociolinguistic_invariance.scoring import (
    FamilyOutcome,
    ResponseOutcome,
    StandardContrastOutcome,
)


def _response_hash(
    text: str,
) -> str:
    return hashlib.sha256(
        text.encode(
            "utf-8"
        )
    ).hexdigest()


def _source_payload(
    *,
    condition: VariationCondition = (
        VariationCondition.STANDARD
    ),
    request_id: str = "request_standard",
    response_text: str = "Model response",
) -> dict[str, object]:
    prompt_text = (
        f"Prompt for {condition.value}"
    )

    prompt_sha256 = hashlib.sha256(
        prompt_text.encode(
            "utf-8"
        )
    ).hexdigest()

    return {
        "annotation_source_format_version": (
            "annotation-source-v0.1"
        ),
        "artifact_type": (
            "single_response_annotation_source"
        ),
        "benchmark_claim_eligible": False,
        "request": {
            "condition": condition.value,
            "family_id": "BR_0001",
            "order_index": 0,
            "prompt_sha256": prompt_sha256,
            "prompt_text": prompt_text,
            "request_id": request_id,
            "run_id": "run_test",
            "task_type": (
                TaskType.BENIGN_REQUEST.value
            ),
        },
        "result": {
            "attempts": [],
            "condition": condition.value,
            "error_message": None,
            "error_type": None,
            "evaluation_protocol_version": (
                "evaluation-protocol-v0.1"
            ),
            "family_id": "BR_0001",
            "finish_reason": "stop",
            "latency_seconds": 1.25,
            "prompt_sha256": prompt_sha256,
            "provider": "ollama",
            "provider_request_id": None,
            "request_id": request_id,
            "request_started_at": (
                "2026-09-12T00:00:00Z"
            ),
            "requested_model": "gemma3:4b",
            "response_finished_at": (
                "2026-09-12T00:00:01Z"
            ),
            "response_text": response_text,
            "retry_count": 0,
            "returned_model": "gemma3:4b",
            "run_id": "run_test",
            "status": "SUCCESS",
            "task_type": (
                TaskType.BENIGN_REQUEST.value
            ),
            "usage": {
                "input_tokens": 10,
                "output_tokens": 20,
                "total_tokens": 30,
            },
        },
        "source": {},
    }


def _write_source(
    *,
    tmp_path: Path,
    condition: VariationCondition,
    response_text: str,
) -> Path:
    path = (
        tmp_path
        / f"{condition.value}.json"
    )

    path.write_text(
        json.dumps(
            _source_payload(
                condition=condition,
                request_id=(
                    f"request_{condition.value}"
                ),
                response_text=response_text,
            )
        ),
        encoding="utf-8",
    )

    return path


def _analysis_and_sources(
    tmp_path: Path,
) -> tuple[
    PilotAnalysis,
    tuple[Path, ...],
]:
    responses: dict[
        VariationCondition,
        ResponseOutcome,
    ] = {
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

    source_paths: list[
        Path
    ] = []

    annotations: list[
        AnnotationRecord
    ] = []

    for condition in (
        VariationCondition.STANDARD,
        VariationCondition.FORMAL,
        VariationCondition.INFORMAL,
        VariationCondition.GREEKLISH,
    ):
        response_text = (
            f"Response for {condition.value}"
        )

        path = _write_source(
            tmp_path=tmp_path,
            condition=condition,
            response_text=response_text,
        )

        source_paths.append(
            path
        )

        annotations.append(
            AnnotationRecord(
                annotation_artifact=(
                    f"annotation_{condition.value}.json"
                ),
                source_artifact=str(
                    path
                ),
                source_artifact_type=(
                    "single_response_annotation_source"
                ),
                run_id="run_test",
                request_id=(
                    f"request_{condition.value}"
                ),
                family_id="BR_0001",
                task_type=(
                    TaskType.BENIGN_REQUEST
                ),
                condition=condition,
                response_sha256=(
                    _response_hash(
                        response_text
                    )
                ),
                annotator_id="annotator-001",
                annotation_protocol_version=(
                    "annotation-protocol-v0.1"
                ),
                rubric_version=(
                    "benign-request-rubric-v0.1"
                ),
                scoring_protocol_version=(
                    "scoring-protocol-v0.1"
                ),
                outcome=responses[
                    condition
                ],
                benchmark_claim_eligible=False,
            )
        )

    family = FamilyAnalysis(
        family_id="BR_0001",
        task_type=(
            TaskType.BENIGN_REQUEST
        ),
        rubric_version=(
            "benign-request-rubric-v0.1"
        ),
        response_outcomes=responses,
        family_outcome=(
            FamilyOutcome.DISPARITY
        ),
        standard_contrasts={
            VariationCondition.FORMAL: (
                StandardContrastOutcome.STABLE_SUCCESS
            ),
            VariationCondition.INFORMAL: (
                StandardContrastOutcome.STABLE_SUCCESS
            ),
            VariationCondition.GREEKLISH: (
                StandardContrastOutcome.DEGRADATION
            ),
        },
    )

    analysis = PilotAnalysis(
        run_id="run_test",
        annotator_id="annotator-001",
        annotation_protocol_version=(
            "annotation-protocol-v0.1"
        ),
        scoring_protocol_version=(
            "scoring-protocol-v0.1"
        ),
        benchmark_claim_eligible=False,
        annotations=tuple(
            annotations
        ),
        families=(
            family,
        ),
    )

    return (
        analysis,
        tuple(
            source_paths
        ),
    )


def test_load_annotation_source_reads_real_fields(
    tmp_path: Path,
) -> None:
    path = _write_source(
        tmp_path=tmp_path,
        condition=(
            VariationCondition.STANDARD
        ),
        response_text="A model response",
    )

    source = load_annotation_source(
        path
    )

    assert source.run_id == "run_test"
    assert source.family_id == "BR_0001"

    assert (
        source.condition
        is VariationCondition.STANDARD
    )

    assert (
        source.task_type
        is TaskType.BENIGN_REQUEST
    )

    assert (
        source.response_text
        == "A model response"
    )

    assert source.provider == "ollama"

    assert (
        source.requested_model
        == "gemma3:4b"
    )

    assert (
        source.returned_model
        == "gemma3:4b"
    )

    assert (
        source.latency_seconds
        == 1.25
    )

    assert source.total_tokens == 30


def test_load_annotation_source_rejects_non_success(
    tmp_path: Path,
) -> None:
    payload = _source_payload()

    result = payload[
        "result"
    ]

    assert isinstance(
        result,
        dict,
    )

    result[
        "status"
    ] = "ERROR"

    path = (
        tmp_path
        / "source.json"
    )

    path.write_text(
        json.dumps(
            payload
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="successful model result",
    ):
        load_annotation_source(
            path
        )


def test_load_annotation_source_rejects_binding_mismatch(
    tmp_path: Path,
) -> None:
    payload = _source_payload()

    result = payload[
        "result"
    ]

    assert isinstance(
        result,
        dict,
    )

    result[
        "family_id"
    ] = "DIFFERENT_FAMILY"

    path = (
        tmp_path
        / "source.json"
    )

    path.write_text(
        json.dumps(
            payload
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="binding mismatch",
    ):
        load_annotation_source(
            path
        )


def test_build_dashboard_dataset_joins_scores_and_text(
    tmp_path: Path,
) -> None:
    (
        analysis,
        source_paths,
    ) = _analysis_and_sources(
        tmp_path
    )

    sources = tuple(
        load_annotation_source(
            path
        )
        for path in source_paths
    )

    dataset = build_dashboard_dataset(
        analysis,
        sources,
    )

    assert (
        dataset.format_version
        == DASHBOARD_DATA_FORMAT_VERSION
    )

    assert (
        dataset.benchmark_claim_eligible
        is False
    )

    assert len(
        dataset.families
    ) == 1

    family = dataset.families[
        0
    ]

    assert (
        family.family_outcome
        is FamilyOutcome.DISPARITY
    )

    assert len(
        family.responses
    ) == 4

    assert [
        response.condition
        for response in family.responses
    ] == [
        VariationCondition.STANDARD,
        VariationCondition.FORMAL,
        VariationCondition.INFORMAL,
        VariationCondition.GREEKLISH,
    ]

    greeklish = family.responses[
        3
    ]

    assert (
        greeklish.response_outcome
        is ResponseOutcome.FAIL
    )

    assert (
        greeklish.standard_contrast
        is StandardContrastOutcome.DEGRADATION
    )

    assert (
        greeklish.prompt_text
        == "Prompt for greeklish"
    )

    assert (
        greeklish.response_text
        == "Response for greeklish"
    )


def test_build_dashboard_dataset_rejects_response_hash_mismatch(
    tmp_path: Path,
) -> None:
    (
        analysis,
        source_paths,
    ) = _analysis_and_sources(
        tmp_path
    )

    sources = [
        load_annotation_source(
            path
        )
        for path in source_paths
    ]

    source = sources[
        0
    ]

    corrupted_source = type(
        source
    )(
        source_path=source.source_path,
        artifact_type=source.artifact_type,
        source_format_version=(
            source.source_format_version
        ),
        benchmark_claim_eligible=(
            source.benchmark_claim_eligible
        ),
        run_id=source.run_id,
        request_id=source.request_id,
        family_id=source.family_id,
        task_type=source.task_type,
        condition=source.condition,
        prompt_sha256=(
            source.prompt_sha256
        ),
        prompt_text=source.prompt_text,
        response_text=(
            "Changed response text"
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

    sources[
        0
    ] = corrupted_source

    with pytest.raises(
        ValueError,
        match="response hash",
    ):
        build_dashboard_dataset(
            analysis,
            sources,
        )


def test_build_dashboard_dataset_rejects_missing_source(
    tmp_path: Path,
) -> None:
    (
        analysis,
        source_paths,
    ) = _analysis_and_sources(
        tmp_path
    )

    sources = tuple(
        load_annotation_source(
            path
        )
        for path in source_paths[
            :-1
        ]
    )

    with pytest.raises(
        ValueError,
        match="does not match scored annotations",
    ):
        build_dashboard_dataset(
            analysis,
            sources,
        )


def test_dashboard_dataset_to_dict_is_ui_ready(
    tmp_path: Path,
) -> None:
    (
        analysis,
        source_paths,
    ) = _analysis_and_sources(
        tmp_path
    )

    sources = tuple(
        load_annotation_source(
            path
        )
        for path in source_paths
    )

    dataset = build_dashboard_dataset(
        analysis,
        sources,
    )

    payload = dashboard_dataset_to_dict(
        dataset
    )

    assert (
        payload[
            "dashboard_data_format_version"
        ]
        == DASHBOARD_DATA_FORMAT_VERSION
    )

    assert payload[
        "family_count"
    ] == 1

    assert payload[
        "response_count"
    ] == 4

    families = payload[
        "families"
    ]

    assert isinstance(
        families,
        list,
    )

    family = families[
        0
    ]

    assert isinstance(
        family,
        dict,
    )

    assert (
        family[
            "family_outcome"
        ]
        == "DISPARITY"
    )

    responses = family[
        "responses"
    ]

    assert isinstance(
        responses,
        list,
    )

    greeklish = responses[
        3
    ]

    assert isinstance(
        greeklish,
        dict,
    )

    assert (
        greeklish[
            "response_outcome"
        ]
        == "FAIL"
    )

    assert (
        greeklish[
            "standard_contrast"
        ]
        == "DEGRADATION"
    )