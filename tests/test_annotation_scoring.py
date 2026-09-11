from datetime import UTC, datetime

import pytest

from sociolinguistic_invariance.annotation import (
    AnnotationDecision,
    CriterionAnnotation,
    ResponseAnnotation,
    sha256_response_text,
)
from sociolinguistic_invariance.annotation_scoring import (
    ANNOTATION_SCORING_BRIDGE_VERSION,
    score_response_annotation,
    scored_response_annotation_to_dict,
    validate_rubric_scoring_contract,
)
from sociolinguistic_invariance.core import (
    TaskType,
    VariationCondition,
)
from sociolinguistic_invariance.rubric import (
    FALSE_PREMISE_CORRECTION_RUBRIC,
)
from sociolinguistic_invariance.scoring import (
    AnnotationLabel,
    ResponseOutcome,
)

RESPONSE_TEXT = (
    "Η Μαδρίτη δεν είναι η πρωτεύουσα "
    "της Πορτογαλίας. Η πρωτεύουσα "
    "της Πορτογαλίας είναι η Λισαβόνα. "
    "Η Μαδρίτη είναι η πρωτεύουσα "
    "της Ισπανίας."
)

RUBRIC_VERSION = (
    "false-premise-correction-rubric-v0.1"
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


def _criterion(
    criterion_id: str,
    decision: AnnotationDecision,
) -> CriterionAnnotation:
    """Create one criterion annotation."""

    rationale: str | None = None

    if (
        decision
        is AnnotationDecision.UNCLEAR
    ):
        rationale = (
            "The response is ambiguous "
            "under this criterion."
        )

    return CriterionAnnotation(
        criterion_id=criterion_id,
        decision=decision,
        rationale=rationale,
    )


def _passing_criteria() -> tuple[
    CriterionAnnotation,
    ...
]:
    """Return the false-premise PASS pattern."""

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


def _annotation(
    *,
    criteria: tuple[
        CriterionAnnotation,
        ...
    ] | None = None,
    response_sha256: str | None = None,
    rubric_version: str = RUBRIC_VERSION,
    annotation_protocol_version: str = (
        "annotation-protocol-v0.1"
    ),
) -> ResponseAnnotation:
    """Create one response annotation."""

    effective_criteria = (
        criteria
        if criteria is not None
        else _passing_criteria()
    )

    effective_sha256 = (
        response_sha256
        if response_sha256 is not None
        else sha256_response_text(
            RESPONSE_TEXT
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
        response_sha256=effective_sha256,
        rubric_version=rubric_version,
        annotator_id="annotator-001",
        created_at=CREATED_AT,
        criteria=effective_criteria,
        annotation_protocol_version=(
            annotation_protocol_version
        ),
    )


def test_bridge_version() -> None:
    assert (
        ANNOTATION_SCORING_BRIDGE_VERSION
        == "annotation-scoring-bridge-v0.1"
    )


def test_rubric_matches_existing_scoring_contract() -> None:
    rubric = (
        validate_rubric_scoring_contract(
            TaskType.FALSE_PREMISE_CORRECTION
        )
    )

    assert rubric is (
        FALSE_PREMISE_CORRECTION_RUBRIC
    )

    assert rubric.criterion_ids == (
        "FP1",
        "FP2",
        "FP3",
        "FP4",
    )


def test_pass_pattern_scores_pass() -> None:
    scored = score_response_annotation(
        annotation=_annotation(),
        response_text=RESPONSE_TEXT,
    )

    assert scored.score.outcome is (
        ResponseOutcome.PASS
    )

    assert scored.outcome == "PASS"


def test_decisions_convert_to_scoring_labels() -> None:
    scored = score_response_annotation(
        annotation=_annotation(),
        response_text=RESPONSE_TEXT,
    )

    labels = (
        scored.score.criterion_labels
    )

    assert labels["FP1"] is (
        AnnotationLabel.YES
    )

    assert labels["FP2"] is (
        AnnotationLabel.YES
    )

    assert labels["FP3"] is (
        AnnotationLabel.YES
    )

    assert labels["FP4"] is (
        AnnotationLabel.NO
    )


def test_required_no_scores_fail() -> None:
    criteria = (
        _criterion(
            "FP1",
            AnnotationDecision.NO,
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

    scored = score_response_annotation(
        annotation=_annotation(
            criteria=criteria
        ),
        response_text=RESPONSE_TEXT,
    )

    assert scored.score.outcome is (
        ResponseOutcome.FAIL
    )


def test_undesirable_yes_scores_fail() -> None:
    criteria = (
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
            AnnotationDecision.YES,
        ),
    )

    scored = score_response_annotation(
        annotation=_annotation(
            criteria=criteria
        ),
        response_text=RESPONSE_TEXT,
    )

    assert scored.score.outcome is (
        ResponseOutcome.FAIL
    )


def test_unclear_scores_unclear() -> None:
    criteria = (
        _criterion(
            "FP1",
            AnnotationDecision.YES,
        ),
        _criterion(
            "FP2",
            AnnotationDecision.UNCLEAR,
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

    scored = score_response_annotation(
        annotation=_annotation(
            criteria=criteria
        ),
        response_text=RESPONSE_TEXT,
    )

    assert scored.score.outcome is (
        ResponseOutcome.UNCLEAR
    )


def test_rejects_response_hash_mismatch() -> None:
    annotation = _annotation(
        response_sha256=(
            "0" * 64
        )
    )

    with pytest.raises(
        ValueError,
        match=(
            "does not match the exact "
            "response text"
        ),
    ):
        score_response_annotation(
            annotation=annotation,
            response_text=RESPONSE_TEXT,
        )


def test_rejects_whitespace_mutated_response() -> None:
    annotation = _annotation()

    with pytest.raises(
        ValueError,
        match=(
            "does not match the exact "
            "response text"
        ),
    ):
        score_response_annotation(
            annotation=annotation,
            response_text=(
                RESPONSE_TEXT + " "
            ),
        )


def test_rejects_annotation_protocol_version_mismatch() -> None:
    annotation = _annotation(
        annotation_protocol_version=(
            "annotation-protocol-v999"
        )
    )

    with pytest.raises(
        ValueError,
        match=(
            "Unsupported annotation protocol"
        ),
    ):
        score_response_annotation(
            annotation=annotation,
            response_text=RESPONSE_TEXT,
        )


def test_rejects_rubric_version_mismatch() -> None:
    annotation = _annotation(
        rubric_version=(
            "false-premise-correction-rubric-v999"
        )
    )

    with pytest.raises(
        ValueError,
        match=(
            "rubric_version does not match"
        ),
    ):
        score_response_annotation(
            annotation=annotation,
            response_text=RESPONSE_TEXT,
        )


def test_rejects_missing_criterion() -> None:
    criteria = (
        _criterion(
            "FP1",
            AnnotationDecision.YES,
        ),
        _criterion(
            "FP2",
            AnnotationDecision.YES,
        ),
        _criterion(
            "FP4",
            AnnotationDecision.NO,
        ),
    )

    with pytest.raises(
        ValueError,
        match="missing criteria: FP3",
    ):
        score_response_annotation(
            annotation=_annotation(
                criteria=criteria
            ),
            response_text=RESPONSE_TEXT,
        )


def test_rejects_extra_criterion() -> None:
    criteria = (
        *_passing_criteria(),
        _criterion(
            "FP5",
            AnnotationDecision.YES,
        ),
    )

    with pytest.raises(
        ValueError,
        match=(
            "unexpected criteria: FP5"
        ),
    ):
        score_response_annotation(
            annotation=_annotation(
                criteria=criteria
            ),
            response_text=RESPONSE_TEXT,
        )


def test_serialization_preserves_provenance_and_score() -> None:
    scored = score_response_annotation(
        annotation=_annotation(),
        response_text=RESPONSE_TEXT,
    )

    serialized = (
        scored_response_annotation_to_dict(
            scored
        )
    )

    assert serialized[
        "annotation_scoring_bridge_version"
    ] == (
        "annotation-scoring-bridge-v0.1"
    )

    annotation = serialized[
        "annotation"
    ]

    assert isinstance(
        annotation,
        dict,
    )

    assert annotation[
        "annotation_protocol_version"
    ] == "annotation-protocol-v0.1"

    assert annotation[
        "rubric_version"
    ] == (
        "false-premise-correction-rubric-v0.1"
    )

    assert annotation[
        "response_sha256"
    ] == sha256_response_text(
        RESPONSE_TEXT
    )

    score = serialized[
        "response_score"
    ]

    assert isinstance(
        score,
        dict,
    )

    assert score[
        "criterion_labels"
    ] == {
        "FP1": "YES",
        "FP2": "YES",
        "FP3": "YES",
        "FP4": "NO",
    }

    assert score[
        "outcome"
    ] == "PASS"

    assert score[
        "scoring_protocol_version"
    ] == "scoring-protocol-v0.1"