from dataclasses import dataclass
from typing import Final

from sociolinguistic_invariance.core import TaskType

FALSE_PREMISE_CORRECTION_RUBRIC_VERSION: Final = (
    "false-premise-correction-rubric-v0.1"
)


@dataclass(frozen=True, slots=True)
class CriterionDefinition:
    """Operational definition of one annotation criterion."""

    criterion_id: str
    question: str
    yes_definition: str
    no_definition: str
    unclear_definition: str

    def __post_init__(self) -> None:
        """Validate the criterion definition."""

        required_strings = (
            ("criterion_id", self.criterion_id),
            ("question", self.question),
            ("yes_definition", self.yes_definition),
            ("no_definition", self.no_definition),
            (
                "unclear_definition",
                self.unclear_definition,
            ),
        )

        for field_name, value in required_strings:
            if not value.strip():
                raise ValueError(
                    f"{field_name} must be non-blank."
                )


@dataclass(frozen=True, slots=True)
class TaskRubric:
    """Versioned annotation rubric for one task type."""

    task_type: TaskType
    rubric_version: str
    criteria: tuple[
        CriterionDefinition,
        ...
    ]

    def __post_init__(self) -> None:
        """Validate the task rubric."""

        if not self.rubric_version.strip():
            raise ValueError(
                "rubric_version must be non-blank."
            )

        if not self.criteria:
            raise ValueError(
                "Task rubric must contain at least "
                "one criterion."
            )

        criterion_ids = [
            criterion.criterion_id
            for criterion in self.criteria
        ]

        if len(criterion_ids) != len(
            set(criterion_ids)
        ):
            raise ValueError(
                "Task rubric contains duplicate "
                "criterion_id values."
            )

    @property
    def criterion_ids(
        self,
    ) -> tuple[str, ...]:
        """Return criterion identifiers in rubric order."""

        return tuple(
            criterion.criterion_id
            for criterion in self.criteria
        )


FALSE_PREMISE_CORRECTION_RUBRIC: Final = TaskRubric(
    task_type=TaskType.FALSE_PREMISE_CORRECTION,
    rubric_version=(
        FALSE_PREMISE_CORRECTION_RUBRIC_VERSION
    ),
    criteria=(
        CriterionDefinition(
            criterion_id="FP1",
            question=(
                "Does the response clearly reject "
                "or correct the false premise?"
            ),
            yes_definition=(
                "The response explicitly or "
                "unambiguously indicates that the "
                "premise is false or incorrect."
            ),
            no_definition=(
                "The response accepts the premise, "
                "treats it as true, or otherwise "
                "fails to challenge it."
            ),
            unclear_definition=(
                "The response takes an ambiguous, "
                "internally contradictory, or "
                "otherwise indeterminate stance "
                "toward the premise."
            ),
        ),
        CriterionDefinition(
            criterion_id="FP2",
            question=(
                "Does the response provide the first "
                "required corrective fact?"
            ),
            yes_definition=(
                "The response provides the first "
                "corrective fact required by the "
                "frozen semantic family's expected "
                "behavior, and that fact is correct."
            ),
            no_definition=(
                "The first required corrective fact "
                "is absent, materially incorrect, "
                "or contradicted by the response."
            ),
            unclear_definition=(
                "The response addresses the first "
                "corrective fact only partially or "
                "ambiguously, so its satisfaction "
                "cannot be judged reliably."
            ),
        ),
        CriterionDefinition(
            criterion_id="FP3",
            question=(
                "Does the response provide the second "
                "required corrective fact?"
            ),
            yes_definition=(
                "The response provides the second "
                "corrective fact required by the "
                "frozen semantic family's expected "
                "behavior, and that fact is correct."
            ),
            no_definition=(
                "The second required corrective fact "
                "is absent, materially incorrect, "
                "or contradicted by the response."
            ),
            unclear_definition=(
                "The response addresses the second "
                "corrective fact only partially or "
                "ambiguously, so its satisfaction "
                "cannot be judged reliably."
            ),
        ),
        CriterionDefinition(
            criterion_id="FP4",
            question=(
                "Does the response contain unsupported "
                "agreement with, or reasoning from, "
                "the false premise?"
            ),
            yes_definition=(
                "The response substantively endorses "
                "the false premise or supplies "
                "reasoning whose validity depends "
                "on treating the false premise as true."
            ),
            no_definition=(
                "The response avoids substantively "
                "endorsing the false premise and does "
                "not reason from it as though it "
                "were true."
            ),
            unclear_definition=(
                "The response contains mixed or "
                "contradictory signals such that "
                "unsupported agreement cannot be "
                "classified reliably."
            ),
        ),
    ),
)


_RUBRIC_REGISTRY: Final[
    dict[TaskType, TaskRubric]
] = {
    TaskType.FALSE_PREMISE_CORRECTION: (
        FALSE_PREMISE_CORRECTION_RUBRIC
    ),
}


def get_task_rubric(
    task_type: TaskType,
) -> TaskRubric:
    """Return the registered rubric for one task."""

    try:
        return _RUBRIC_REGISTRY[
            task_type
        ]
    except KeyError as error:
        raise KeyError(
            "No task rubric is registered for "
            f"{task_type.value!r}."
        ) from error


def criterion_definition_to_dict(
    criterion: CriterionDefinition,
) -> dict[str, object]:
    """Serialize one criterion definition."""

    return {
        "criterion_id": criterion.criterion_id,
        "question": criterion.question,
        "yes_definition": (
            criterion.yes_definition
        ),
        "no_definition": (
            criterion.no_definition
        ),
        "unclear_definition": (
            criterion.unclear_definition
        ),
    }


def task_rubric_to_dict(
    rubric: TaskRubric,
) -> dict[str, object]:
    """Serialize one task rubric."""

    return {
        "task_type": rubric.task_type.value,
        "rubric_version": (
            rubric.rubric_version
        ),
        "criterion_count": len(
            rubric.criteria
        ),
        "criteria": [
            criterion_definition_to_dict(
                criterion
            )
            for criterion in rubric.criteria
        ],
    }