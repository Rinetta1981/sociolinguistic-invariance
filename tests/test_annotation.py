from datetime import UTC, datetime

import pytest

from sociolinguistic_invariance.annotation import (
    ANNOTATION_PROTOCOL_VERSION,
    AnnotationDecision,
    CriterionAnnotation,
    ResponseAnnotation,
    criterion_annotation_to_dict,
    response_annotation_to_dict,
    sha256_response_text,
)
from sociolinguistic_invariance.core import (
    TaskType,
    VariationCondition,
)

RESPONSE_TEXT = (
    "Η Μαδρίτη δεν είναι η πρωτεύουσα "
    "της Πορτογαλίας. Η πρωτεύουσα "
    "της Πορτογαλίας είναι η Λισαβόνα."
)

EXPECTED_SHA256 = sha256_response_text(
    RESPONSE_TEXT
)

RUBRIC_VERSION = (
    "false-premise-correction-rubric-v0.1"
)

CREATED_AT = datetime(
    2026,
    9,
    11,
    15,
    0,
    0,
    tzinfo=UTC,
)


def _criterion(
    *,
    criterion_id: str = "FP1",
    decision: AnnotationDecision = (
        AnnotationDecision.YES
    ),
    rationale: str | None = None,
    evidence: str | None = None,
) -> CriterionAnnotation:
    """Create one criterion annotation."""

    return CriterionAnnotation(
        criterion_id=criterion_id,
        decision=decision,
        rationale=rationale,
        evidence=evidence,
    )


def _annotation(
    *,
    response_sha256: str = EXPECTED_SHA256,
    rubric_version: str = RUBRIC_VERSION,
    annotator_id: str = "annotator-001",
    created_at: datetime = CREATED_AT,
    criteria: tuple[
        CriterionAnnotation,
        ...
    ] | None = None,
) -> ResponseAnnotation:
    """Create one complete response annotation."""

    effective_criteria = (
        criteria
        if criteria is not None
        else (
            _criterion(),
        )
    )

    return ResponseAnnotation(
        run_id="run_test",
        request_id="req_test",
        family_id="FP_0001",
        task_type=(
            TaskType.FALSE_PREMISE_CORRECTION
        ),
        condition=VariationCondition.STANDARD,
        response_sha256=response_sha256,
        rubric_version=rubric_version,
        annotator_id=annotator_id,
        created_at=created_at,
        criteria=effective_criteria,
    )


def test_annotation_protocol_version() -> None:
    assert ANNOTATION_PROTOCOL_VERSION == (
        "annotation-protocol-v0.1"
    )


def test_annotation_decision_values() -> None:
    assert [
        decision.value
        for decision in AnnotationDecision
    ] == [
        "YES",
        "NO",
        "UNCLEAR",
    ]


def test_sha256_response_text_is_deterministic() -> None:
    first = sha256_response_text(
        RESPONSE_TEXT
    )

    second = sha256_response_text(
        RESPONSE_TEXT
    )

    assert first == second
    assert len(first) == 64


def test_sha256_changes_when_response_changes() -> None:
    original = sha256_response_text(
        RESPONSE_TEXT
    )

    changed = sha256_response_text(
        RESPONSE_TEXT + " "
    )

    assert original != changed


def test_criterion_accepts_yes() -> None:
    criterion = _criterion(
        decision=AnnotationDecision.YES
    )

    assert criterion.decision is (
        AnnotationDecision.YES
    )


def test_criterion_accepts_no() -> None:
    criterion = _criterion(
        decision=AnnotationDecision.NO
    )

    assert criterion.decision is (
        AnnotationDecision.NO
    )


def test_unclear_criterion_requires_rationale() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "UNCLEAR criterion annotations "
            "require a rationale"
        ),
    ):
        _criterion(
            decision=(
                AnnotationDecision.UNCLEAR
            )
        )


def test_unclear_criterion_accepts_rationale() -> None:
    criterion = _criterion(
        decision=(
            AnnotationDecision.UNCLEAR
        ),
        rationale=(
            "The answer is too ambiguous "
            "to classify reliably."
        ),
    )

    assert criterion.decision is (
        AnnotationDecision.UNCLEAR
    )


def test_criterion_rejects_blank_id() -> None:
    with pytest.raises(
        ValueError,
        match="criterion_id must be non-blank",
    ):
        _criterion(
            criterion_id="   "
        )


def test_criterion_rejects_blank_rationale() -> None:
    with pytest.raises(
        ValueError,
        match="rationale must be non-blank",
    ):
        _criterion(
            rationale="   "
        )


def test_criterion_rejects_blank_evidence() -> None:
    with pytest.raises(
        ValueError,
        match="evidence must be non-blank",
    ):
        _criterion(
            evidence="   "
        )


def test_response_annotation_is_valid() -> None:
    annotation = _annotation()

    assert annotation.run_id == "run_test"
    assert annotation.request_id == "req_test"
    assert annotation.family_id == "FP_0001"
    assert annotation.criterion_count == 1


def test_response_annotation_preserves_rubric_version() -> None:
    annotation = _annotation()

    assert annotation.rubric_version == (
        "false-premise-correction-rubric-v0.1"
    )


def test_response_annotation_rejects_blank_rubric_version() -> None:
    with pytest.raises(
        ValueError,
        match="rubric_version must be non-blank",
    ):
        _annotation(
            rubric_version="   "
        )


def test_response_annotation_rejects_bad_sha256() -> None:
    with pytest.raises(
        ValueError,
        match="response_sha256",
    ):
        _annotation(
            response_sha256="not-a-hash"
        )


def test_response_annotation_rejects_uppercase_sha256() -> None:
    with pytest.raises(
        ValueError,
        match="response_sha256",
    ):
        _annotation(
            response_sha256="A" * 64
        )


def test_response_annotation_rejects_blank_annotator() -> None:
    with pytest.raises(
        ValueError,
        match="annotator_id must be non-blank",
    ):
        _annotation(
            annotator_id="   "
        )


def test_response_annotation_rejects_naive_datetime() -> None:
    naive_datetime = datetime(
        2026,
        9,
        11,
        15,
        0,
        0,
    )

    with pytest.raises(
        ValueError,
        match="created_at must be timezone-aware",
    ):
        _annotation(
            created_at=naive_datetime
        )


def test_response_annotation_requires_criterion() -> None:
    with pytest.raises(
        ValueError,
        match="at least one criterion",
    ):
        _annotation(
            criteria=()
        )


def test_response_annotation_rejects_duplicate_criteria() -> None:
    duplicate = (
        _criterion(
            criterion_id="FP1"
        ),
        _criterion(
            criterion_id="FP1"
        ),
    )

    with pytest.raises(
        ValueError,
        match="duplicate criterion_id",
    ):
        _annotation(
            criteria=duplicate
        )


def test_decision_counts_include_all_labels() -> None:
    annotation = _annotation(
        criteria=(
            _criterion(
                criterion_id="FP1",
                decision=AnnotationDecision.YES,
            ),
            _criterion(
                criterion_id="FP2",
                decision=AnnotationDecision.NO,
            ),
            _criterion(
                criterion_id="FP3",
                decision=(
                    AnnotationDecision.UNCLEAR
                ),
                rationale="Ambiguous response.",
            ),
        )
    )

    assert annotation.decision_counts == {
        "YES": 1,
        "NO": 1,
        "UNCLEAR": 1,
    }


def test_decision_counts_include_zero_categories() -> None:
    annotation = _annotation()

    assert annotation.decision_counts == {
        "YES": 1,
        "NO": 0,
        "UNCLEAR": 0,
    }


def test_criterion_serialization() -> None:
    criterion = _criterion(
        evidence=(
            "Η Μαδρίτη δεν είναι η "
            "πρωτεύουσα της Πορτογαλίας."
        )
    )

    assert criterion_annotation_to_dict(
        criterion
    ) == {
        "criterion_id": "FP1",
        "decision": "YES",
        "rationale": None,
        "evidence": (
            "Η Μαδρίτη δεν είναι η "
            "πρωτεύουσα της Πορτογαλίας."
        ),
    }


def test_response_annotation_serialization() -> None:
    annotation = _annotation(
        criteria=(
            _criterion(
                evidence=(
                    "Η Μαδρίτη δεν είναι η "
                    "πρωτεύουσα της "
                    "Πορτογαλίας."
                )
            ),
        )
    )

    serialized = response_annotation_to_dict(
        annotation
    )

    assert serialized[
        "annotation_protocol_version"
    ] == "annotation-protocol-v0.1"

    assert serialized[
        "rubric_version"
    ] == (
        "false-premise-correction-rubric-v0.1"
    )

    assert serialized["run_id"] == "run_test"
    assert serialized["request_id"] == "req_test"
    assert serialized["family_id"] == "FP_0001"

    assert serialized[
        "task_type"
    ] == "false_premise_correction"

    assert serialized[
        "condition"
    ] == "standard"

    assert serialized[
        "response_sha256"
    ] == EXPECTED_SHA256

    assert serialized[
        "annotator_id"
    ] == "annotator-001"

    assert serialized[
        "created_at"
    ] == "2026-09-11T15:00:00+00:00"

    assert serialized[
        "criterion_count"
    ] == 1

    assert serialized[
        "decision_counts"
    ] == {
        "YES": 1,
        "NO": 0,
        "UNCLEAR": 0,
    }


def test_serialized_criteria_are_ordered() -> None:
    annotation = _annotation(
        criteria=(
            _criterion(
                criterion_id="FP1"
            ),
            _criterion(
                criterion_id="FP2"
            ),
        )
    )

    serialized = response_annotation_to_dict(
        annotation
    )

    criteria = serialized["criteria"]

    assert isinstance(
        criteria,
        list,
    )

    assert [
        criterion["criterion_id"]
        for criterion in criteria
    ] == [
        "FP1",
        "FP2",
    ]