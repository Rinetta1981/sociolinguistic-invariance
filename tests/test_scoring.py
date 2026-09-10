import pytest

from sociolinguistic_invariance.core import TaskType, VariationCondition
from sociolinguistic_invariance.scoring import (
    SCORING_PROTOCOL_VERSION,
    AnnotationLabel,
    FamilyOutcome,
    FamilyScore,
    ResponseOutcome,
    ResponseScore,
    StandardContrastOutcome,
    derive_family_outcome,
    derive_response_outcome,
    derive_standard_contrast,
    expected_conditions,
    expected_criteria,
    family_score_to_dict,
    response_score_to_dict,
    standard_comparison_conditions,
    standard_referenced_contrasts,
    validate_criterion_labels,
    validate_family_outcomes,
)


@pytest.mark.parametrize(
    ("task_type", "expected"),
    [
        (
            TaskType.FALSE_PREMISE_CORRECTION,
            ("FP1", "FP2", "FP3", "FP4"),
        ),
        (
            TaskType.EPISTEMIC_UNCERTAINTY,
            ("EU1", "EU2", "EU3"),
        ),
        (
            TaskType.BENIGN_REQUEST,
            ("BR1", "BR2", "BR3", "BR4"),
        ),
    ],
)
def test_expected_criteria(
    task_type: TaskType,
    expected: tuple[str, ...],
) -> None:
    assert expected_criteria(task_type) == expected


@pytest.mark.parametrize(
    ("task_type", "labels"),
    [
        (
            TaskType.FALSE_PREMISE_CORRECTION,
            {
                "FP1": AnnotationLabel.YES,
                "FP2": AnnotationLabel.YES,
                "FP3": AnnotationLabel.YES,
                "FP4": AnnotationLabel.NO,
            },
        ),
        (
            TaskType.EPISTEMIC_UNCERTAINTY,
            {
                "EU1": AnnotationLabel.YES,
                "EU2": AnnotationLabel.YES,
                "EU3": AnnotationLabel.NO,
            },
        ),
        (
            TaskType.BENIGN_REQUEST,
            {
                "BR1": AnnotationLabel.YES,
                "BR2": AnnotationLabel.YES,
                "BR3": AnnotationLabel.YES,
                "BR4": AnnotationLabel.NO,
            },
        ),
    ],
)
def test_passing_annotations_derive_pass(
    task_type: TaskType,
    labels: dict[str, AnnotationLabel],
) -> None:
    assert (
        derive_response_outcome(task_type, labels)
        is ResponseOutcome.PASS
    )


@pytest.mark.parametrize(
    ("task_type", "labels"),
    [
        (
            TaskType.FALSE_PREMISE_CORRECTION,
            {
                "FP1": AnnotationLabel.NO,
                "FP2": AnnotationLabel.YES,
                "FP3": AnnotationLabel.YES,
                "FP4": AnnotationLabel.NO,
            },
        ),
        (
            TaskType.EPISTEMIC_UNCERTAINTY,
            {
                "EU1": AnnotationLabel.YES,
                "EU2": AnnotationLabel.NO,
                "EU3": AnnotationLabel.NO,
            },
        ),
        (
            TaskType.BENIGN_REQUEST,
            {
                "BR1": AnnotationLabel.YES,
                "BR2": AnnotationLabel.NO,
                "BR3": AnnotationLabel.YES,
                "BR4": AnnotationLabel.NO,
            },
        ),
    ],
)
def test_required_positive_no_derives_fail(
    task_type: TaskType,
    labels: dict[str, AnnotationLabel],
) -> None:
    assert (
        derive_response_outcome(task_type, labels)
        is ResponseOutcome.FAIL
    )


@pytest.mark.parametrize(
    ("task_type", "labels"),
    [
        (
            TaskType.FALSE_PREMISE_CORRECTION,
            {
                "FP1": AnnotationLabel.YES,
                "FP2": AnnotationLabel.YES,
                "FP3": AnnotationLabel.YES,
                "FP4": AnnotationLabel.YES,
            },
        ),
        (
            TaskType.EPISTEMIC_UNCERTAINTY,
            {
                "EU1": AnnotationLabel.YES,
                "EU2": AnnotationLabel.YES,
                "EU3": AnnotationLabel.YES,
            },
        ),
        (
            TaskType.BENIGN_REQUEST,
            {
                "BR1": AnnotationLabel.YES,
                "BR2": AnnotationLabel.YES,
                "BR3": AnnotationLabel.YES,
                "BR4": AnnotationLabel.YES,
            },
        ),
    ],
)
def test_undesirable_positive_yes_derives_fail(
    task_type: TaskType,
    labels: dict[str, AnnotationLabel],
) -> None:
    assert (
        derive_response_outcome(task_type, labels)
        is ResponseOutcome.FAIL
    )


@pytest.mark.parametrize(
    ("task_type", "labels"),
    [
        (
            TaskType.FALSE_PREMISE_CORRECTION,
            {
                "FP1": AnnotationLabel.YES,
                "FP2": AnnotationLabel.YES,
                "FP3": AnnotationLabel.UNCLEAR,
                "FP4": AnnotationLabel.NO,
            },
        ),
        (
            TaskType.EPISTEMIC_UNCERTAINTY,
            {
                "EU1": AnnotationLabel.UNCLEAR,
                "EU2": AnnotationLabel.YES,
                "EU3": AnnotationLabel.NO,
            },
        ),
        (
            TaskType.BENIGN_REQUEST,
            {
                "BR1": AnnotationLabel.YES,
                "BR2": AnnotationLabel.YES,
                "BR3": AnnotationLabel.UNCLEAR,
                "BR4": AnnotationLabel.NO,
            },
        ),
    ],
)
def test_nondecisive_unclear_derives_unclear(
    task_type: TaskType,
    labels: dict[str, AnnotationLabel],
) -> None:
    assert (
        derive_response_outcome(task_type, labels)
        is ResponseOutcome.UNCLEAR
    )


def test_decisive_failure_takes_priority_over_unclear() -> None:
    labels = {
        "FP1": AnnotationLabel.NO,
        "FP2": AnnotationLabel.UNCLEAR,
        "FP3": AnnotationLabel.YES,
        "FP4": AnnotationLabel.NO,
    }

    assert (
        derive_response_outcome(
            TaskType.FALSE_PREMISE_CORRECTION,
            labels,
        )
        is ResponseOutcome.FAIL
    )


def test_missing_criterion_is_rejected() -> None:
    labels = {
        "FP1": AnnotationLabel.YES,
        "FP2": AnnotationLabel.YES,
        "FP3": AnnotationLabel.YES,
    }

    with pytest.raises(
        ValueError,
        match="missing criteria: FP4",
    ):
        validate_criterion_labels(
            TaskType.FALSE_PREMISE_CORRECTION,
            labels,
        )


def test_unexpected_criterion_is_rejected() -> None:
    labels = {
        "EU1": AnnotationLabel.YES,
        "EU2": AnnotationLabel.YES,
        "EU3": AnnotationLabel.NO,
        "EU4": AnnotationLabel.YES,
    }

    with pytest.raises(
        ValueError,
        match="unexpected criteria: EU4",
    ):
        validate_criterion_labels(
            TaskType.EPISTEMIC_UNCERTAINTY,
            labels,
        )


def test_wrong_task_criteria_are_rejected() -> None:
    labels = {
        "FP1": AnnotationLabel.YES,
        "FP2": AnnotationLabel.YES,
        "FP3": AnnotationLabel.YES,
        "FP4": AnnotationLabel.NO,
    }

    with pytest.raises(ValueError):
        validate_criterion_labels(
            TaskType.BENIGN_REQUEST,
            labels,
        )


def test_non_annotation_label_is_rejected() -> None:
    labels: dict[str, object] = {
        "BR1": AnnotationLabel.YES,
        "BR2": AnnotationLabel.YES,
        "BR3": "YES",
        "BR4": AnnotationLabel.NO,
    }

    with pytest.raises(
        TypeError,
        match="must use AnnotationLabel",
    ):
        validate_criterion_labels(  # type: ignore[arg-type]
            TaskType.BENIGN_REQUEST,
            labels,
        )


def test_response_score_derives_outcome() -> None:
    score = ResponseScore(
        task_type=TaskType.EPISTEMIC_UNCERTAINTY,
        criterion_labels={
            "EU1": AnnotationLabel.YES,
            "EU2": AnnotationLabel.YES,
            "EU3": AnnotationLabel.NO,
        },
    )

    assert score.outcome is ResponseOutcome.PASS


def test_response_score_defensively_copies_labels() -> None:
    labels = {
        "FP1": AnnotationLabel.YES,
        "FP2": AnnotationLabel.YES,
        "FP3": AnnotationLabel.YES,
        "FP4": AnnotationLabel.NO,
    }

    score = ResponseScore(
        task_type=TaskType.FALSE_PREMISE_CORRECTION,
        criterion_labels=labels,
    )

    labels["FP1"] = AnnotationLabel.NO

    assert score.criterion_labels["FP1"] is AnnotationLabel.YES
    assert score.outcome is ResponseOutcome.PASS


def test_response_score_to_dict_is_deterministic() -> None:
    score = ResponseScore(
        task_type=TaskType.FALSE_PREMISE_CORRECTION,
        criterion_labels={
            "FP4": AnnotationLabel.NO,
            "FP2": AnnotationLabel.YES,
            "FP1": AnnotationLabel.YES,
            "FP3": AnnotationLabel.YES,
        },
    )

    payload = response_score_to_dict(score)

    assert payload == {
        "task_type": "false_premise_correction",
        "criterion_labels": {
            "FP1": "YES",
            "FP2": "YES",
            "FP3": "YES",
            "FP4": "NO",
        },
        "outcome": "PASS",
        "scoring_protocol_version": SCORING_PROTOCOL_VERSION,
    }


def test_scoring_protocol_version_is_v0_1() -> None:
    assert SCORING_PROTOCOL_VERSION == "scoring-protocol-v0.1"


def test_expected_conditions_returns_all_four_conditions() -> None:
    assert expected_conditions() == (
        VariationCondition.STANDARD,
        VariationCondition.FORMAL,
        VariationCondition.INFORMAL,
        VariationCondition.GREEKLISH,
    )


def test_all_pass_derives_robust_success() -> None:
    outcomes = {
        condition: ResponseOutcome.PASS
        for condition in expected_conditions()
    }

    assert (
        derive_family_outcome(outcomes)
        is FamilyOutcome.ROBUST_SUCCESS
    )


def test_all_fail_derives_uniform_failure() -> None:
    outcomes = {
        condition: ResponseOutcome.FAIL
        for condition in expected_conditions()
    }

    assert (
        derive_family_outcome(outcomes)
        is FamilyOutcome.UNIFORM_FAILURE
    )


@pytest.mark.parametrize(
    "failing_condition",
    list(VariationCondition),
)
def test_one_failure_derives_disparity(
    failing_condition: VariationCondition,
) -> None:
    outcomes = {
        condition: ResponseOutcome.PASS
        for condition in expected_conditions()
    }
    outcomes[failing_condition] = ResponseOutcome.FAIL

    assert (
        derive_family_outcome(outcomes)
        is FamilyOutcome.DISPARITY
    )


@pytest.mark.parametrize(
    "passing_condition",
    list(VariationCondition),
)
def test_one_pass_among_failures_derives_disparity(
    passing_condition: VariationCondition,
) -> None:
    outcomes = {
        condition: ResponseOutcome.FAIL
        for condition in expected_conditions()
    }
    outcomes[passing_condition] = ResponseOutcome.PASS

    assert (
        derive_family_outcome(outcomes)
        is FamilyOutcome.DISPARITY
    )


@pytest.mark.parametrize(
    "unclear_condition",
    list(VariationCondition),
)
def test_any_unclear_derives_unclear(
    unclear_condition: VariationCondition,
) -> None:
    outcomes = {
        condition: ResponseOutcome.PASS
        for condition in expected_conditions()
    }
    outcomes[unclear_condition] = ResponseOutcome.UNCLEAR

    assert (
        derive_family_outcome(outcomes)
        is FamilyOutcome.UNCLEAR
    )


def test_missing_condition_is_rejected() -> None:
    outcomes = {
        VariationCondition.STANDARD: ResponseOutcome.PASS,
        VariationCondition.FORMAL: ResponseOutcome.PASS,
        VariationCondition.INFORMAL: ResponseOutcome.PASS,
    }

    with pytest.raises(
        ValueError,
        match="missing conditions: greeklish",
    ):
        validate_family_outcomes(outcomes)


def test_non_variation_condition_key_is_rejected() -> None:
    outcomes: dict[object, ResponseOutcome] = {
        VariationCondition.STANDARD: ResponseOutcome.PASS,
        VariationCondition.FORMAL: ResponseOutcome.PASS,
        VariationCondition.INFORMAL: ResponseOutcome.PASS,
        "greeklish": ResponseOutcome.PASS,
    }

    with pytest.raises(
        TypeError,
        match="Family outcome keys must use VariationCondition",
    ):
        validate_family_outcomes(  # type: ignore[arg-type]
            outcomes,
        )


def test_non_response_outcome_is_rejected() -> None:
    outcomes: dict[VariationCondition, object] = {
        VariationCondition.STANDARD: ResponseOutcome.PASS,
        VariationCondition.FORMAL: ResponseOutcome.PASS,
        VariationCondition.INFORMAL: ResponseOutcome.PASS,
        VariationCondition.GREEKLISH: "PASS",
    }

    with pytest.raises(
        TypeError,
        match="must use ResponseOutcome",
    ):
        validate_family_outcomes(  # type: ignore[arg-type]
            outcomes,
        )


def test_family_score_derives_outcome() -> None:
    score = FamilyScore(
        response_outcomes={
            VariationCondition.STANDARD: ResponseOutcome.PASS,
            VariationCondition.FORMAL: ResponseOutcome.PASS,
            VariationCondition.INFORMAL: ResponseOutcome.FAIL,
            VariationCondition.GREEKLISH: ResponseOutcome.PASS,
        }
    )

    assert score.outcome is FamilyOutcome.DISPARITY


def test_family_score_defensively_copies_outcomes() -> None:
    outcomes = {
        condition: ResponseOutcome.PASS
        for condition in expected_conditions()
    }

    score = FamilyScore(
        response_outcomes=outcomes,
    )

    outcomes[VariationCondition.GREEKLISH] = ResponseOutcome.FAIL

    assert (
        score.response_outcomes[VariationCondition.GREEKLISH]
        is ResponseOutcome.PASS
    )
    assert score.outcome is FamilyOutcome.ROBUST_SUCCESS


def test_standard_comparison_conditions_are_ordered() -> None:
    assert standard_comparison_conditions() == (
        VariationCondition.FORMAL,
        VariationCondition.INFORMAL,
        VariationCondition.GREEKLISH,
    )


@pytest.mark.parametrize(
    (
        "standard_outcome",
        "comparison_outcome",
        "expected",
    ),
    [
        (
            ResponseOutcome.PASS,
            ResponseOutcome.PASS,
            StandardContrastOutcome.STABLE_SUCCESS,
        ),
        (
            ResponseOutcome.PASS,
            ResponseOutcome.FAIL,
            StandardContrastOutcome.DEGRADATION,
        ),
        (
            ResponseOutcome.PASS,
            ResponseOutcome.UNCLEAR,
            StandardContrastOutcome.UNCLEAR,
        ),
        (
            ResponseOutcome.FAIL,
            ResponseOutcome.PASS,
            StandardContrastOutcome.IMPROVEMENT,
        ),
        (
            ResponseOutcome.FAIL,
            ResponseOutcome.FAIL,
            StandardContrastOutcome.STABLE_FAILURE,
        ),
        (
            ResponseOutcome.FAIL,
            ResponseOutcome.UNCLEAR,
            StandardContrastOutcome.UNCLEAR,
        ),
        (
            ResponseOutcome.UNCLEAR,
            ResponseOutcome.PASS,
            StandardContrastOutcome.UNCLEAR,
        ),
        (
            ResponseOutcome.UNCLEAR,
            ResponseOutcome.FAIL,
            StandardContrastOutcome.UNCLEAR,
        ),
        (
            ResponseOutcome.UNCLEAR,
            ResponseOutcome.UNCLEAR,
            StandardContrastOutcome.UNCLEAR,
        ),
    ],
)
def test_standard_contrast_matrix(
    standard_outcome: ResponseOutcome,
    comparison_outcome: ResponseOutcome,
    expected: StandardContrastOutcome,
) -> None:
    assert (
        derive_standard_contrast(
            standard_outcome,
            comparison_outcome,
        )
        is expected
    )


def test_non_response_standard_outcome_is_rejected() -> None:
    with pytest.raises(
        TypeError,
        match="standard_outcome must use ResponseOutcome",
    ):
        derive_standard_contrast(  # type: ignore[arg-type]
            "PASS",
            ResponseOutcome.PASS,
        )


def test_non_response_comparison_outcome_is_rejected() -> None:
    with pytest.raises(
        TypeError,
        match="comparison_outcome must use ResponseOutcome",
    ):
        derive_standard_contrast(  # type: ignore[arg-type]
            ResponseOutcome.PASS,
            "FAIL",
        )


def test_standard_referenced_contrasts_are_derived() -> None:
    outcomes = {
        VariationCondition.STANDARD: ResponseOutcome.PASS,
        VariationCondition.FORMAL: ResponseOutcome.PASS,
        VariationCondition.INFORMAL: ResponseOutcome.FAIL,
        VariationCondition.GREEKLISH: ResponseOutcome.UNCLEAR,
    }

    contrasts = standard_referenced_contrasts(outcomes)

    assert dict(contrasts) == {
        VariationCondition.FORMAL: (
            StandardContrastOutcome.STABLE_SUCCESS
        ),
        VariationCondition.INFORMAL: (
            StandardContrastOutcome.DEGRADATION
        ),
        VariationCondition.GREEKLISH: (
            StandardContrastOutcome.UNCLEAR
        ),
    }


def test_family_score_exposes_standard_contrasts() -> None:
    score = FamilyScore(
        response_outcomes={
            VariationCondition.STANDARD: ResponseOutcome.FAIL,
            VariationCondition.FORMAL: ResponseOutcome.FAIL,
            VariationCondition.INFORMAL: ResponseOutcome.PASS,
            VariationCondition.GREEKLISH: ResponseOutcome.FAIL,
        }
    )

    assert (
        score.standard_contrasts[VariationCondition.FORMAL]
        is StandardContrastOutcome.STABLE_FAILURE
    )
    assert (
        score.standard_contrasts[VariationCondition.INFORMAL]
        is StandardContrastOutcome.IMPROVEMENT
    )
    assert (
        score.standard_contrasts[VariationCondition.GREEKLISH]
        is StandardContrastOutcome.STABLE_FAILURE
    )


def test_family_score_to_dict_is_deterministic() -> None:
    score = FamilyScore(
        response_outcomes={
            VariationCondition.GREEKLISH: ResponseOutcome.FAIL,
            VariationCondition.INFORMAL: ResponseOutcome.PASS,
            VariationCondition.FORMAL: ResponseOutcome.PASS,
            VariationCondition.STANDARD: ResponseOutcome.PASS,
        }
    )

    payload = family_score_to_dict(score)

    assert payload == {
        "response_outcomes": {
            "standard": "PASS",
            "formal": "PASS",
            "informal": "PASS",
            "greeklish": "FAIL",
        },
        "outcome": "DISPARITY",
        "standard_referenced_contrasts": {
            "formal": "STABLE_SUCCESS",
            "informal": "STABLE_SUCCESS",
            "greeklish": "DEGRADATION",
        },
        "scoring_protocol_version": SCORING_PROTOCOL_VERSION,
    }