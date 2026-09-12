from sociolinguistic_invariance.core import (
    TaskType,
    VariationCondition,
)
from sociolinguistic_invariance.pilot_analysis import (
    AnnotationRecord,
    FamilyAnalysis,
    PilotAnalysis,
)
from sociolinguistic_invariance.pilot_reporting import (
    PILOT_REPORT_FORMAT_VERSION,
    render_pilot_report,
)
from sociolinguistic_invariance.scoring import (
    FamilyOutcome,
    ResponseOutcome,
    StandardContrastOutcome,
)


def _record(
    *,
    family_id: str,
    task_type: TaskType,
    condition: VariationCondition,
    outcome: ResponseOutcome,
    rubric_version: str,
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
        run_id="run_test",
        request_id=(
            f"request_{family_id}_"
            f"{condition.value}"
        ),
        family_id=family_id,
        task_type=task_type,
        condition=condition,
        response_sha256="a" * 64,
        annotator_id="annotator-001",
        annotation_protocol_version=(
            "annotation-protocol-v0.1"
        ),
        rubric_version=rubric_version,
        scoring_protocol_version=(
            "scoring-protocol-v0.1"
        ),
        outcome=outcome,
        benchmark_claim_eligible=False,
    )


def _family(
    *,
    family_id: str,
    task_type: TaskType,
    rubric_version: str,
    greeklish_outcome: ResponseOutcome,
) -> FamilyAnalysis:
    response_outcomes = {
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
            greeklish_outcome
        ),
    }

    family_outcome = (
        FamilyOutcome.ROBUST_SUCCESS
        if (
            greeklish_outcome
            is ResponseOutcome.PASS
        )
        else FamilyOutcome.DISPARITY
    )

    greeklish_contrast = (
        StandardContrastOutcome.STABLE_SUCCESS
        if (
            greeklish_outcome
            is ResponseOutcome.PASS
        )
        else StandardContrastOutcome.DEGRADATION
    )

    return FamilyAnalysis(
        family_id=family_id,
        task_type=task_type,
        rubric_version=rubric_version,
        response_outcomes=response_outcomes,
        family_outcome=family_outcome,
        standard_contrasts={
            VariationCondition.FORMAL: (
                StandardContrastOutcome.STABLE_SUCCESS
            ),
            VariationCondition.INFORMAL: (
                StandardContrastOutcome.STABLE_SUCCESS
            ),
            VariationCondition.GREEKLISH: (
                greeklish_contrast
            ),
        },
    )


def _analysis() -> PilotAnalysis:
    families = (
        _family(
            family_id="FP_0001",
            task_type=(
                TaskType.FALSE_PREMISE_CORRECTION
            ),
            rubric_version=(
                "false-premise-correction-rubric-v0.1"
            ),
            greeklish_outcome=(
                ResponseOutcome.FAIL
            ),
        ),
        _family(
            family_id="EU_0001",
            task_type=(
                TaskType.EPISTEMIC_UNCERTAINTY
            ),
            rubric_version=(
                "epistemic-uncertainty-rubric-v0.1"
            ),
            greeklish_outcome=(
                ResponseOutcome.FAIL
            ),
        ),
        _family(
            family_id="BR_0001",
            task_type=(
                TaskType.BENIGN_REQUEST
            ),
            rubric_version=(
                "benign-request-rubric-v0.1"
            ),
            greeklish_outcome=(
                ResponseOutcome.PASS
            ),
        ),
    )

    annotations: list[
        AnnotationRecord
    ] = []

    for family in families:
        for (
            condition,
            outcome,
        ) in family.response_outcomes.items():
            annotations.append(
                _record(
                    family_id=family.family_id,
                    task_type=family.task_type,
                    condition=condition,
                    outcome=outcome,
                    rubric_version=(
                        family.rubric_version
                    ),
                )
            )

    return PilotAnalysis(
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
        families=families,
    )


def test_report_has_expected_title_and_version(
) -> None:
    report = render_pilot_report(
        _analysis()
    )

    assert (
        "# Sociolinguistic Invariance — "
        "Discovery Pilot Report"
        in report
    )

    assert (
        PILOT_REPORT_FORMAT_VERSION
        in report
    )


def test_report_marks_discovery_scope(
) -> None:
    report = render_pilot_report(
        _analysis()
    )

    assert (
        "benchmark_claim_eligible=false"
        in report
    )

    assert (
        "must not be presented as "
        "confirmatory benchmark claims"
        in report
    )


def test_report_contains_response_counts(
) -> None:
    report = render_pilot_report(
        _analysis()
    )

    assert "| PASS | 10 |" in report
    assert "| FAIL | 2 |" in report
    assert "| UNCLEAR | 0 |" in report


def test_report_contains_family_counts(
) -> None:
    report = render_pilot_report(
        _analysis()
    )

    assert (
        "| ROBUST_SUCCESS | 1 |"
        in report
    )

    assert (
        "| DISPARITY | 2 |"
        in report
    )


def test_report_contains_contrast_counts(
) -> None:
    report = render_pilot_report(
        _analysis()
    )

    assert (
        "| STABLE_SUCCESS | 7 |"
        in report
    )

    assert (
        "| DEGRADATION | 2 |"
        in report
    )


def test_report_contains_all_family_outcomes(
) -> None:
    report = render_pilot_report(
        _analysis()
    )

    assert (
        "| `FP_0001` | "
        "False-premise correction | "
        "**DISPARITY** |"
        in report
    )

    assert (
        "| `EU_0001` | "
        "Epistemic uncertainty | "
        "**DISPARITY** |"
        in report
    )

    assert (
        "| `BR_0001` | "
        "Benign request | "
        "**ROBUST_SUCCESS** |"
        in report
    )


def test_report_marks_greeklish_degradations(
) -> None:
    report = render_pilot_report(
        _analysis()
    )

    assert (
        "| Greeklish | **FAIL** | "
        "DEGRADATION |"
        in report
    )

    assert (
        "2 of these involved the "
        "Greeklish condition"
        in report
    )


def test_report_does_not_overclaim(
) -> None:
    report = render_pilot_report(
        _analysis()
    )

    assert (
        "do not establish that Greeklish"
        in report
    )

    assert (
        "No inferential significance tests "
        "are reported"
        in report
    )

    assert (
        "fresh held-out semantic families"
        in report
    )