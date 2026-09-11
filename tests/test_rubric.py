import pytest

from sociolinguistic_invariance.core import (
    TaskType,
)
from sociolinguistic_invariance.rubric import (
    FALSE_PREMISE_CORRECTION_RUBRIC,
    FALSE_PREMISE_CORRECTION_RUBRIC_VERSION,
    CriterionDefinition,
    TaskRubric,
    criterion_definition_to_dict,
    get_task_rubric,
    task_rubric_to_dict,
)


def _criterion(
    *,
    criterion_id: str = "criterion-a",
    question: str = "Does the response satisfy A?",
    yes_definition: str = "Yes means A is satisfied.",
    no_definition: str = "No means A is not satisfied.",
    unclear_definition: str = (
        "Unclear means A cannot be determined."
    ),
) -> CriterionDefinition:
    """Create one valid criterion definition."""

    return CriterionDefinition(
        criterion_id=criterion_id,
        question=question,
        yes_definition=yes_definition,
        no_definition=no_definition,
        unclear_definition=unclear_definition,
    )


def test_false_premise_rubric_version() -> None:
    assert (
        FALSE_PREMISE_CORRECTION_RUBRIC_VERSION
        == "false-premise-correction-rubric-v0.1"
    )


def test_criterion_definition_is_valid() -> None:
    criterion = _criterion()

    assert criterion.criterion_id == (
        "criterion-a"
    )

    assert criterion.question == (
        "Does the response satisfy A?"
    )


def test_criterion_rejects_blank_id() -> None:
    with pytest.raises(
        ValueError,
        match="criterion_id must be non-blank",
    ):
        _criterion(
            criterion_id="   "
        )


def test_criterion_rejects_blank_question() -> None:
    with pytest.raises(
        ValueError,
        match="question must be non-blank",
    ):
        _criterion(
            question="   "
        )


def test_criterion_rejects_blank_yes_definition() -> None:
    with pytest.raises(
        ValueError,
        match="yes_definition must be non-blank",
    ):
        _criterion(
            yes_definition="   "
        )


def test_criterion_rejects_blank_no_definition() -> None:
    with pytest.raises(
        ValueError,
        match="no_definition must be non-blank",
    ):
        _criterion(
            no_definition="   "
        )


def test_criterion_rejects_blank_unclear_definition() -> None:
    with pytest.raises(
        ValueError,
        match="unclear_definition must be non-blank",
    ):
        _criterion(
            unclear_definition="   "
        )


def test_task_rubric_preserves_criterion_order() -> None:
    rubric = TaskRubric(
        task_type=(
            TaskType.FALSE_PREMISE_CORRECTION
        ),
        rubric_version="test-rubric-v1",
        criteria=(
            _criterion(
                criterion_id="first"
            ),
            _criterion(
                criterion_id="second"
            ),
        ),
    )

    assert rubric.criterion_ids == (
        "first",
        "second",
    )


def test_task_rubric_rejects_blank_version() -> None:
    with pytest.raises(
        ValueError,
        match="rubric_version must be non-blank",
    ):
        TaskRubric(
            task_type=(
                TaskType.FALSE_PREMISE_CORRECTION
            ),
            rubric_version="   ",
            criteria=(
                _criterion(),
            ),
        )


def test_task_rubric_requires_criterion() -> None:
    with pytest.raises(
        ValueError,
        match="at least one criterion",
    ):
        TaskRubric(
            task_type=(
                TaskType.FALSE_PREMISE_CORRECTION
            ),
            rubric_version="test-rubric-v1",
            criteria=(),
        )


def test_task_rubric_rejects_duplicate_criterion_ids() -> None:
    with pytest.raises(
        ValueError,
        match="duplicate criterion_id",
    ):
        TaskRubric(
            task_type=(
                TaskType.FALSE_PREMISE_CORRECTION
            ),
            rubric_version="test-rubric-v1",
            criteria=(
                _criterion(
                    criterion_id="duplicate"
                ),
                _criterion(
                    criterion_id="duplicate"
                ),
            ),
        )


def test_registry_returns_false_premise_rubric() -> None:
    rubric = get_task_rubric(
        TaskType.FALSE_PREMISE_CORRECTION
    )

    assert rubric is (
        FALSE_PREMISE_CORRECTION_RUBRIC
    )


def test_registry_rejects_epistemic_uncertainty() -> None:
    with pytest.raises(
        KeyError,
        match="No task rubric is registered",
    ):
        get_task_rubric(
            TaskType.EPISTEMIC_UNCERTAINTY
        )


def test_registry_rejects_benign_request() -> None:
    with pytest.raises(
        KeyError,
        match="No task rubric is registered",
    ):
        get_task_rubric(
            TaskType.BENIGN_REQUEST
        )


def test_false_premise_criterion_ids_match_scoring_contract() -> None:
    assert (
        FALSE_PREMISE_CORRECTION_RUBRIC
        .criterion_ids
    ) == (
        "FP1",
        "FP2",
        "FP3",
        "FP4",
    )


def test_false_premise_criteria_have_complete_definitions() -> None:
    for criterion in (
        FALSE_PREMISE_CORRECTION_RUBRIC
        .criteria
    ):
        assert criterion.question.strip()
        assert criterion.yes_definition.strip()
        assert criterion.no_definition.strip()
        assert (
            criterion
            .unclear_definition
            .strip()
        )


def test_criterion_serialization() -> None:
    criterion = _criterion()

    assert criterion_definition_to_dict(
        criterion
    ) == {
        "criterion_id": "criterion-a",
        "question": (
            "Does the response satisfy A?"
        ),
        "yes_definition": (
            "Yes means A is satisfied."
        ),
        "no_definition": (
            "No means A is not satisfied."
        ),
        "unclear_definition": (
            "Unclear means A cannot "
            "be determined."
        ),
    }


def test_task_rubric_serialization() -> None:
    serialized = task_rubric_to_dict(
        FALSE_PREMISE_CORRECTION_RUBRIC
    )

    assert serialized[
        "task_type"
    ] == "false_premise_correction"

    assert serialized[
        "rubric_version"
    ] == (
        "false-premise-correction-rubric-v0.1"
    )

    assert serialized[
        "criterion_count"
    ] == 4

    criteria = serialized[
        "criteria"
    ]

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
        "FP3",
        "FP4",
    ]