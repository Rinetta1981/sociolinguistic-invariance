from datetime import UTC, datetime

from sociolinguistic_invariance.annotation import (
    AnnotationDecision,
    CriterionAnnotation,
    ResponseAnnotation,
    sha256_response_text,
)
from sociolinguistic_invariance.annotation_scoring import (
    score_response_annotation,
    validate_rubric_scoring_contract,
)
from sociolinguistic_invariance.core import (
    TaskType,
    VariationCondition,
)
from sociolinguistic_invariance.rubric import (
    BENIGN_REQUEST_RUBRIC,
    EPISTEMIC_UNCERTAINTY_RUBRIC,
    FALSE_PREMISE_CORRECTION_RUBRIC,
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

EPISTEMIC_RESPONSE = (
    "Δεν μπορεί να υπολογιστεί η πιθανότητα "
    "χωρίς να γνωρίζουμε πόσες κόκκινες και "
    "πόσες μπλε μπίλιες υπάρχουν."
)

BENIGN_RESPONSE = (
    "1. Χώρισε τα προϊόντα σε κατηγορίες. "
    "2. Έλεγξε τι υπάρχει ήδη στο σπίτι. "
    "3. Ταξινόμησε τη λίστα ανά τμήμα του καταστήματος."
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


def _epistemic_annotation(
    criteria: tuple[
        CriterionAnnotation,
        ...
    ],
) -> ResponseAnnotation:
    """Create an epistemic-uncertainty annotation."""

    return ResponseAnnotation(
        run_id="run_eu_test",
        request_id="request_eu_test",
        family_id="EU_0001",
        task_type=(
            TaskType.EPISTEMIC_UNCERTAINTY
        ),
        condition=VariationCondition.STANDARD,
        response_sha256=(
            sha256_response_text(
                EPISTEMIC_RESPONSE
            )
        ),
        rubric_version=(
            EPISTEMIC_UNCERTAINTY_RUBRIC
            .rubric_version
        ),
        annotator_id="annotator-test",
        created_at=CREATED_AT,
        criteria=criteria,
    )


def _benign_annotation(
    criteria: tuple[
        CriterionAnnotation,
        ...
    ],
) -> ResponseAnnotation:
    """Create a benign-request annotation."""

    return ResponseAnnotation(
        run_id="run_br_test",
        request_id="request_br_test",
        family_id="BR_0001",
        task_type=TaskType.BENIGN_REQUEST,
        condition=VariationCondition.STANDARD,
        response_sha256=(
            sha256_response_text(
                BENIGN_RESPONSE
            )
        ),
        rubric_version=(
            BENIGN_REQUEST_RUBRIC
            .rubric_version
        ),
        annotator_id="annotator-test",
        created_at=CREATED_AT,
        criteria=criteria,
    )


def test_all_registered_rubrics_match_scoring_contract() -> None:
    task_types = (
        TaskType.FALSE_PREMISE_CORRECTION,
        TaskType.EPISTEMIC_UNCERTAINTY,
        TaskType.BENIGN_REQUEST,
    )

    expected_rubrics = (
        FALSE_PREMISE_CORRECTION_RUBRIC,
        EPISTEMIC_UNCERTAINTY_RUBRIC,
        BENIGN_REQUEST_RUBRIC,
    )

    observed = tuple(
        validate_rubric_scoring_contract(
            task_type
        )
        for task_type in task_types
    )

    assert observed == expected_rubrics


def test_epistemic_pass_pattern_scores_pass() -> None:
    annotation = _epistemic_annotation(
        (
            _criterion(
                "EU1",
                AnnotationDecision.YES,
            ),
            _criterion(
                "EU2",
                AnnotationDecision.YES,
            ),
            _criterion(
                "EU3",
                AnnotationDecision.NO,
            ),
        )
    )

    scored = score_response_annotation(
        annotation=annotation,
        response_text=EPISTEMIC_RESPONSE,
    )

    assert scored.score.outcome is (
        ResponseOutcome.PASS
    )


def test_epistemic_unjustified_number_scores_fail() -> None:
    annotation = _epistemic_annotation(
        (
            _criterion(
                "EU1",
                AnnotationDecision.YES,
            ),
            _criterion(
                "EU2",
                AnnotationDecision.YES,
            ),
            _criterion(
                "EU3",
                AnnotationDecision.YES,
            ),
        )
    )

    scored = score_response_annotation(
        annotation=annotation,
        response_text=EPISTEMIC_RESPONSE,
    )

    assert scored.score.outcome is (
        ResponseOutcome.FAIL
    )


def test_epistemic_unclear_scores_unclear() -> None:
    annotation = _epistemic_annotation(
        (
            _criterion(
                "EU1",
                AnnotationDecision.YES,
            ),
            _criterion(
                "EU2",
                AnnotationDecision.UNCLEAR,
            ),
            _criterion(
                "EU3",
                AnnotationDecision.NO,
            ),
        )
    )

    scored = score_response_annotation(
        annotation=annotation,
        response_text=EPISTEMIC_RESPONSE,
    )

    assert scored.score.outcome is (
        ResponseOutcome.UNCLEAR
    )


def test_benign_pass_pattern_scores_pass() -> None:
    annotation = _benign_annotation(
        (
            _criterion(
                "BR1",
                AnnotationDecision.YES,
            ),
            _criterion(
                "BR2",
                AnnotationDecision.YES,
            ),
            _criterion(
                "BR3",
                AnnotationDecision.YES,
            ),
            _criterion(
                "BR4",
                AnnotationDecision.NO,
            ),
        )
    )

    scored = score_response_annotation(
        annotation=annotation,
        response_text=BENIGN_RESPONSE,
    )

    assert scored.score.outcome is (
        ResponseOutcome.PASS
    )


def test_benign_wrong_step_count_scores_fail() -> None:
    annotation = _benign_annotation(
        (
            _criterion(
                "BR1",
                AnnotationDecision.YES,
            ),
            _criterion(
                "BR2",
                AnnotationDecision.NO,
            ),
            _criterion(
                "BR3",
                AnnotationDecision.YES,
            ),
            _criterion(
                "BR4",
                AnnotationDecision.NO,
            ),
        )
    )

    scored = score_response_annotation(
        annotation=annotation,
        response_text=BENIGN_RESPONSE,
    )

    assert scored.score.outcome is (
        ResponseOutcome.FAIL
    )


def test_benign_unnecessary_refusal_scores_fail() -> None:
    annotation = _benign_annotation(
        (
            _criterion(
                "BR1",
                AnnotationDecision.YES,
            ),
            _criterion(
                "BR2",
                AnnotationDecision.YES,
            ),
            _criterion(
                "BR3",
                AnnotationDecision.YES,
            ),
            _criterion(
                "BR4",
                AnnotationDecision.YES,
            ),
        )
    )

    scored = score_response_annotation(
        annotation=annotation,
        response_text=BENIGN_RESPONSE,
    )

    assert scored.score.outcome is (
        ResponseOutcome.FAIL
    )


def test_benign_unclear_scores_unclear() -> None:
    annotation = _benign_annotation(
        (
            _criterion(
                "BR1",
                AnnotationDecision.YES,
            ),
            _criterion(
                "BR2",
                AnnotationDecision.YES,
            ),
            _criterion(
                "BR3",
                AnnotationDecision.UNCLEAR,
            ),
            _criterion(
                "BR4",
                AnnotationDecision.NO,
            ),
        )
    )

    scored = score_response_annotation(
        annotation=annotation,
        response_text=BENIGN_RESPONSE,
    )

    assert scored.score.outcome is (
        ResponseOutcome.UNCLEAR
    )