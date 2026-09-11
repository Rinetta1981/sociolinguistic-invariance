from dataclasses import dataclass
from typing import Final

from sociolinguistic_invariance.annotation import (
    ANNOTATION_PROTOCOL_VERSION,
    ResponseAnnotation,
    response_annotation_to_dict,
    sha256_response_text,
)
from sociolinguistic_invariance.core import (
    TaskType,
)
from sociolinguistic_invariance.rubric import (
    TaskRubric,
    get_task_rubric,
)
from sociolinguistic_invariance.scoring import (
    AnnotationLabel,
    ResponseScore,
    expected_criteria,
    response_score_to_dict,
)

ANNOTATION_SCORING_BRIDGE_VERSION: Final = (
    "annotation-scoring-bridge-v0.1"
)


@dataclass(frozen=True, slots=True)
class ScoredResponseAnnotation:
    """One verified annotation paired with its score."""

    annotation: ResponseAnnotation
    score: ResponseScore

    def __post_init__(self) -> None:
        """Validate metadata alignment."""

        if (
            self.annotation.task_type
            is not self.score.task_type
        ):
            raise ValueError(
                "Annotation task_type does not match "
                "ResponseScore task_type."
            )

    @property
    def outcome(
        self,
    ) -> str:
        """Return the derived response outcome value."""

        return self.score.outcome.value


def validate_rubric_scoring_contract(
    task_type: TaskType,
) -> TaskRubric:
    """Verify that rubric criteria match scoring criteria."""

    rubric = get_task_rubric(
        task_type
    )

    scoring_criteria = expected_criteria(
        task_type
    )

    if (
        rubric.criterion_ids
        != scoring_criteria
    ):
        raise RuntimeError(
            "Registered rubric criteria do not "
            "match the scoring contract for "
            f"{task_type.value!r}. "
            f"Rubric: {rubric.criterion_ids!r}; "
            f"scoring: {scoring_criteria!r}."
        )

    return rubric


def _validate_response_binding(
    *,
    annotation: ResponseAnnotation,
    response_text: str,
) -> None:
    """Verify annotation binding to exact response text."""

    observed_sha256 = (
        sha256_response_text(
            response_text
        )
    )

    if (
        observed_sha256
        != annotation.response_sha256
    ):
        raise ValueError(
            "Annotation response_sha256 does not "
            "match the exact response text."
        )


def _validate_annotation_protocol(
    annotation: ResponseAnnotation,
) -> None:
    """Require the currently supported annotation protocol."""

    if (
        annotation.annotation_protocol_version
        != ANNOTATION_PROTOCOL_VERSION
    ):
        raise ValueError(
            "Unsupported annotation protocol "
            f"{annotation.annotation_protocol_version!r}; "
            "expected "
            f"{ANNOTATION_PROTOCOL_VERSION!r}."
        )


def _validate_rubric_version(
    *,
    annotation: ResponseAnnotation,
    rubric: TaskRubric,
) -> None:
    """Verify annotation binding to its registered rubric."""

    if (
        annotation.rubric_version
        != rubric.rubric_version
    ):
        raise ValueError(
            "Annotation rubric_version does not "
            "match the registered rubric for "
            f"{annotation.task_type.value!r}. "
            f"Annotation: "
            f"{annotation.rubric_version!r}; "
            f"registered: "
            f"{rubric.rubric_version!r}."
        )


def _validate_annotation_criteria(
    *,
    annotation: ResponseAnnotation,
    rubric: TaskRubric,
) -> None:
    """Require exactly the rubric's criterion set."""

    expected = set(
        rubric.criterion_ids
    )

    actual = {
        criterion.criterion_id
        for criterion in annotation.criteria
    }

    missing = sorted(
        expected - actual
    )

    extra = sorted(
        actual - expected
    )

    if not missing and not extra:
        return

    problems: list[str] = []

    if missing:
        problems.append(
            "missing criteria: "
            + ", ".join(
                missing
            )
        )

    if extra:
        problems.append(
            "unexpected criteria: "
            + ", ".join(
                extra
            )
        )

    raise ValueError(
        "Annotation criteria do not match "
        "the registered rubric: "
        + "; ".join(
            problems
        )
    )


def _criterion_labels(
    annotation: ResponseAnnotation,
) -> dict[str, AnnotationLabel]:
    """Convert annotation decisions to scoring labels."""

    return {
        criterion.criterion_id: (
            AnnotationLabel(
                criterion.decision.value
            )
        )
        for criterion in annotation.criteria
    }


def score_response_annotation(
    *,
    annotation: ResponseAnnotation,
    response_text: str,
) -> ScoredResponseAnnotation:
    """Verify and score one annotated model response."""

    _validate_response_binding(
        annotation=annotation,
        response_text=response_text,
    )

    _validate_annotation_protocol(
        annotation
    )

    rubric = (
        validate_rubric_scoring_contract(
            annotation.task_type
        )
    )

    _validate_rubric_version(
        annotation=annotation,
        rubric=rubric,
    )

    _validate_annotation_criteria(
        annotation=annotation,
        rubric=rubric,
    )

    score = ResponseScore(
        task_type=annotation.task_type,
        criterion_labels=(
            _criterion_labels(
                annotation
            )
        ),
    )

    return ScoredResponseAnnotation(
        annotation=annotation,
        score=score,
    )


def scored_response_annotation_to_dict(
    scored: ScoredResponseAnnotation,
) -> dict[str, object]:
    """Serialize annotation and derived score."""

    return {
        "annotation_scoring_bridge_version": (
            ANNOTATION_SCORING_BRIDGE_VERSION
        ),
        "annotation": (
            response_annotation_to_dict(
                scored.annotation
            )
        ),
        "response_score": (
            response_score_to_dict(
                scored.score
            )
        ),
    }