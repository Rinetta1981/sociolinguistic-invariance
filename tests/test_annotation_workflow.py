import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from sociolinguistic_invariance.annotation import (
    AnnotationDecision,
    CriterionAnnotation,
    ResponseAnnotation,
)
from sociolinguistic_invariance.annotation_workflow import (
    HUMAN_SCORED_RESPONSE_ARTIFACT_FORMAT_VERSION,
    HUMAN_SCORED_RESPONSE_ARTIFACT_TYPE,
    AnnotationSource,
    annotation_artifact_filename,
    annotation_output_path,
    create_scored_response_annotation,
    human_scored_response_artifact_to_dict,
    write_human_scored_response_artifact_atomic,
)
from sociolinguistic_invariance.core import (
    TaskType,
    VariationCondition,
)
from sociolinguistic_invariance.provenance import (
    GitProvenance,
)
from sociolinguistic_invariance.scoring import (
    ResponseOutcome,
)

CREATED_AT = datetime(
    2026,
    9,
    11,
    18,
    0,
    0,
    tzinfo=UTC,
)

RESPONSE_TEXT = (
    "Η Μαδρίτη δεν είναι η πρωτεύουσα "
    "της Πορτογαλίας. Η πρωτεύουσα "
    "της Πορτογαλίας είναι η Λισαβόνα. "
    "Η Μαδρίτη είναι η πρωτεύουσα "
    "της Ισπανίας."
)


def _provenance() -> GitProvenance:
    """Return deterministic test Git provenance."""

    return GitProvenance(
        available=True,
        commit="a" * 40,
        worktree_clean=True,
        status_entry_count=0,
        status_sha256="b" * 64,
    )


def _source(
    *,
    task_type: TaskType = (
        TaskType.FALSE_PREMISE_CORRECTION
    ),
    family_id: str = "FP_0001",
    response_text: str = RESPONSE_TEXT,
    source_benchmark_claim_eligible: bool = False,
    run_id: str = "run_test",
    request_id: str = "request_test",
) -> AnnotationSource:
    """Create one valid annotation source."""

    return AnnotationSource(
        source_artifact=(
            "results/raw/run_test.json"
        ),
        source_artifact_type=(
            "evaluation_run"
        ),
        source_benchmark_claim_eligible=(
            source_benchmark_claim_eligible
        ),
        run_id=run_id,
        request_id=request_id,
        family_id=family_id,
        task_type=task_type,
        condition=VariationCondition.STANDARD,
        response_text=response_text,
    )


def _criterion(
    criterion_id: str,
    decision: AnnotationDecision,
) -> CriterionAnnotation:
    """Create one criterion annotation."""

    return CriterionAnnotation(
        criterion_id=criterion_id,
        decision=decision,
        rationale=None,
        evidence=None,
    )


def _false_premise_criteria(
) -> tuple[
    CriterionAnnotation,
    ...,
]:
    """Return the passing false-premise pattern."""

    return (
        _criterion(
            "FP1",
            AnnotationDecision.YES,
        ),
        _criterion(
            "FP2",
            AnnotationDecision.YES,
        ),
        _criterion(
            "FP3",
            AnnotationDecision.YES,
        ),
        _criterion(
            "FP4",
            AnnotationDecision.NO,
        ),
    )


def test_source_preserves_valid_metadata() -> None:
    source = _source()

    assert source.run_id == "run_test"
    assert source.request_id == "request_test"
    assert source.family_id == "FP_0001"
    assert (
        source.task_type
        is TaskType.FALSE_PREMISE_CORRECTION
    )
    assert (
        source.condition
        is VariationCondition.STANDARD
    )
    assert source.response_text == RESPONSE_TEXT
    assert (
        source.source_benchmark_claim_eligible
        is False
    )


def test_source_rejects_blank_response_text() -> None:
    with pytest.raises(
        ValueError,
        match="response_text must be non-blank",
    ):
        _source(
            response_text="   ",
        )


def test_source_rejects_blank_run_id() -> None:
    with pytest.raises(
        ValueError,
        match="run_id must be non-blank",
    ):
        _source(
            run_id="   ",
        )


def test_create_scored_annotation_passes() -> None:
    scored = create_scored_response_annotation(
        source=_source(),
        annotator_id="annotator-001",
        criteria=_false_premise_criteria(),
        created_at=CREATED_AT,
    )

    assert (
        scored.score.outcome
        is ResponseOutcome.PASS
    )


def test_scored_annotation_preserves_source_binding(
) -> None:
    source = _source()

    scored = create_scored_response_annotation(
        source=source,
        annotator_id="annotator-001",
        criteria=_false_premise_criteria(),
        created_at=CREATED_AT,
    )

    annotation = scored.annotation

    assert annotation.run_id == source.run_id
    assert (
        annotation.request_id
        == source.request_id
    )
    assert (
        annotation.family_id
        == source.family_id
    )
    assert (
        annotation.task_type
        is source.task_type
    )
    assert (
        annotation.condition
        is source.condition
    )


def test_scored_annotation_uses_registered_rubric(
) -> None:
    scored = create_scored_response_annotation(
        source=_source(),
        annotator_id="annotator-001",
        criteria=_false_premise_criteria(),
        created_at=CREATED_AT,
    )

    assert (
        scored.annotation.rubric_version
        == "false-premise-correction-rubric-v0.1"
    )


def test_artifact_metadata_is_preserved() -> None:
    source = _source()

    scored = create_scored_response_annotation(
        source=source,
        annotator_id="annotator-001",
        criteria=_false_premise_criteria(),
        created_at=CREATED_AT,
    )

    artifact = (
        human_scored_response_artifact_to_dict(
            source=source,
            scored=scored,
            git_provenance=_provenance(),
        )
    )

    assert artifact[
        "artifact_type"
    ] == HUMAN_SCORED_RESPONSE_ARTIFACT_TYPE

    assert artifact[
        "artifact_format_version"
    ] == (
        HUMAN_SCORED_RESPONSE_ARTIFACT_FORMAT_VERSION
    )

    assert artifact[
        "source_artifact"
    ] == "results/raw/run_test.json"

    assert artifact[
        "source_artifact_type"
    ] == "evaluation_run"

    assert artifact[
        "source_benchmark_claim_eligible"
    ] is False

    assert artifact[
        "benchmark_claim_eligible"
    ] is False

    assert isinstance(
        artifact["scored_annotation"],
        dict,
    )


def test_artifact_preserves_git_provenance() -> None:
    source = _source()

    scored = create_scored_response_annotation(
        source=source,
        annotator_id="annotator-001",
        criteria=_false_premise_criteria(),
        created_at=CREATED_AT,
    )

    artifact = (
        human_scored_response_artifact_to_dict(
            source=source,
            scored=scored,
            git_provenance=_provenance(),
        )
    )

    provenance = artifact[
        "git_provenance"
    ]

    assert isinstance(
        provenance,
        dict,
    )

    assert provenance[
        "available"
    ] is True

    assert provenance[
        "commit"
    ] == "a" * 40

    assert provenance[
        "worktree_clean"
    ] is True

    assert provenance[
        "status_entry_count"
    ] == 0

    assert provenance[
        "status_sha256"
    ] == "b" * 64


def test_artifact_propagates_claim_eligibility(
) -> None:
    source = _source(
        source_benchmark_claim_eligible=True,
    )

    scored = create_scored_response_annotation(
        source=source,
        annotator_id="annotator-001",
        criteria=_false_premise_criteria(),
        created_at=CREATED_AT,
    )

    artifact = (
        human_scored_response_artifact_to_dict(
            source=source,
            scored=scored,
            git_provenance=_provenance(),
        )
    )

    assert artifact[
        "source_benchmark_claim_eligible"
    ] is True

    assert artifact[
        "benchmark_claim_eligible"
    ] is True


def test_filename_is_deterministic() -> None:
    scored = create_scored_response_annotation(
        source=_source(),
        annotator_id="annotator-001",
        criteria=_false_premise_criteria(),
        created_at=CREATED_AT,
    )

    filename = annotation_artifact_filename(
        scored.annotation
    )

    assert filename == (
        "run_test_FP_0001_standard_"
        "annotator-001.json"
    )


def test_filename_rejects_unsafe_component() -> None:
    annotation = ResponseAnnotation(
        run_id="../unsafe",
        request_id="request_test",
        family_id="FP_0001",
        task_type=(
            TaskType.FALSE_PREMISE_CORRECTION
        ),
        condition=VariationCondition.STANDARD,
        response_sha256="a" * 64,
        rubric_version=(
            "false-premise-correction-rubric-v0.1"
        ),
        annotator_id="annotator-001",
        created_at=CREATED_AT,
        criteria=_false_premise_criteria(),
    )

    with pytest.raises(
        ValueError,
        match="unsafe for an annotation",
    ):
        annotation_artifact_filename(
            annotation
        )


def test_output_path_uses_annotations_directory(
    tmp_path: Path,
) -> None:
    scored = create_scored_response_annotation(
        source=_source(),
        annotator_id="annotator-001",
        criteria=_false_premise_criteria(),
        created_at=CREATED_AT,
    )

    path = annotation_output_path(
        output_directory=tmp_path,
        annotation=scored.annotation,
    )

    assert path == (
        tmp_path
        / (
            "run_test_FP_0001_standard_"
            "annotator-001.json"
        )
    )


def test_atomic_writer_writes_json(
    tmp_path: Path,
) -> None:
    path = (
        tmp_path
        / "annotation.json"
    )

    payload: dict[str, object] = {
        "artifact_type": "test",
        "outcome": "PASS",
    }

    write_human_scored_response_artifact_atomic(
        path=path,
        payload=payload,
    )

    observed = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    assert observed == payload


def test_atomic_writer_refuses_silent_overwrite(
    tmp_path: Path,
) -> None:
    path = (
        tmp_path
        / "annotation.json"
    )

    path.write_text(
        "{}",
        encoding="utf-8",
    )

    with pytest.raises(
        FileExistsError,
        match="already exists",
    ):
        write_human_scored_response_artifact_atomic(
            path=path,
            payload={
                "artifact_type": "test",
            },
        )


def test_atomic_writer_allows_explicit_overwrite(
    tmp_path: Path,
) -> None:
    path = (
        tmp_path
        / "annotation.json"
    )

    path.write_text(
        json.dumps(
            {
                "artifact_type": "old",
                "outcome": "FAIL",
            }
        ),
        encoding="utf-8",
    )

    payload: dict[str, object] = {
        "artifact_type": "test",
        "outcome": "PASS",
    }

    write_human_scored_response_artifact_atomic(
        path=path,
        payload=payload,
        overwrite=True,
    )

    observed = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    assert observed == payload