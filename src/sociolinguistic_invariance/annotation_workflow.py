import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Final

from sociolinguistic_invariance.annotation import (
    CriterionAnnotation,
    ResponseAnnotation,
    sha256_response_text,
)
from sociolinguistic_invariance.annotation_scoring import (
    ScoredResponseAnnotation,
    score_response_annotation,
    scored_response_annotation_to_dict,
)
from sociolinguistic_invariance.batch_execution import (
    write_raw_results_atomic,
)
from sociolinguistic_invariance.core import (
    TaskType,
    VariationCondition,
)
from sociolinguistic_invariance.provenance import (
    GitProvenance,
    git_provenance_to_dict,
)
from sociolinguistic_invariance.rubric import (
    get_task_rubric,
)

HUMAN_SCORED_RESPONSE_ARTIFACT_TYPE: Final = (
    "human_scored_response_annotation"
)

HUMAN_SCORED_RESPONSE_ARTIFACT_FORMAT_VERSION: Final = (
    "human-scored-response-annotation-v0.1"
)

_FILENAME_COMPONENT_PATTERN: Final = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9._-]*$"
)


@dataclass(frozen=True, slots=True)
class AnnotationSource:
    """Exact model response and metadata to be annotated."""

    source_artifact: str
    source_artifact_type: str
    source_benchmark_claim_eligible: bool
    run_id: str
    request_id: str
    family_id: str
    task_type: TaskType
    condition: VariationCondition
    response_text: str

    def __post_init__(self) -> None:
        """Validate source-response metadata."""

        required_strings = (
            (
                "source_artifact",
                self.source_artifact,
            ),
            (
                "source_artifact_type",
                self.source_artifact_type,
            ),
            (
                "run_id",
                self.run_id,
            ),
            (
                "request_id",
                self.request_id,
            ),
            (
                "family_id",
                self.family_id,
            ),
            (
                "response_text",
                self.response_text,
            ),
        )

        for field_name, value in required_strings:
            if not value.strip():
                raise ValueError(
                    f"{field_name} must be non-blank."
                )

        if not isinstance(
            self.source_benchmark_claim_eligible,
            bool,
        ):
            raise TypeError(
                "source_benchmark_claim_eligible "
                "must be a bool."
            )


def create_scored_response_annotation(
    *,
    source: AnnotationSource,
    annotator_id: str,
    criteria: tuple[
        CriterionAnnotation,
        ...
    ],
    created_at: datetime,
) -> ScoredResponseAnnotation:
    """Create, bind, validate, and score one annotation."""

    rubric = get_task_rubric(
        source.task_type
    )

    annotation = ResponseAnnotation(
        run_id=source.run_id,
        request_id=source.request_id,
        family_id=source.family_id,
        task_type=source.task_type,
        condition=source.condition,
        response_sha256=(
            sha256_response_text(
                source.response_text
            )
        ),
        rubric_version=(
            rubric.rubric_version
        ),
        annotator_id=annotator_id,
        created_at=created_at,
        criteria=criteria,
    )

    return score_response_annotation(
        annotation=annotation,
        response_text=source.response_text,
    )


def _validate_source_binding(
    *,
    source: AnnotationSource,
    scored: ScoredResponseAnnotation,
) -> None:
    """Verify that a scored annotation belongs to its source."""

    annotation = scored.annotation

    expected_response_sha256 = (
        sha256_response_text(
            source.response_text
        )
    )

    comparisons = (
        (
            "run_id",
            annotation.run_id,
            source.run_id,
        ),
        (
            "request_id",
            annotation.request_id,
            source.request_id,
        ),
        (
            "family_id",
            annotation.family_id,
            source.family_id,
        ),
        (
            "task_type",
            annotation.task_type,
            source.task_type,
        ),
        (
            "condition",
            annotation.condition,
            source.condition,
        ),
        (
            "response_sha256",
            annotation.response_sha256,
            expected_response_sha256,
        ),
    )

    for field_name, observed, expected in comparisons:
        if observed != expected:
            raise ValueError(
                "Scored annotation does not match "
                "its source for "
                f"{field_name}."
            )


def human_scored_response_artifact_to_dict(
    *,
    source: AnnotationSource,
    scored: ScoredResponseAnnotation,
    git_provenance: GitProvenance,
) -> dict[str, object]:
    """Serialize one auditable human-scored response."""

    _validate_source_binding(
        source=source,
        scored=scored,
    )

    return {
        "artifact_type": (
            HUMAN_SCORED_RESPONSE_ARTIFACT_TYPE
        ),
        "artifact_format_version": (
            HUMAN_SCORED_RESPONSE_ARTIFACT_FORMAT_VERSION
        ),
        "source_artifact": (
            source.source_artifact
        ),
        "source_artifact_type": (
            source.source_artifact_type
        ),
        "source_benchmark_claim_eligible": (
            source.source_benchmark_claim_eligible
        ),
        "git_provenance": (
            git_provenance_to_dict(
                git_provenance
            )
        ),
        "benchmark_claim_eligible": (
            source.source_benchmark_claim_eligible
        ),
        "scored_annotation": (
            scored_response_annotation_to_dict(
                scored
            )
        ),
    }


def _validate_filename_component(
    *,
    field_name: str,
    value: str,
) -> None:
    """Reject unsafe or ambiguous filename components."""

    if (
        not _FILENAME_COMPONENT_PATTERN.fullmatch(
            value
        )
        or ".." in value
    ):
        raise ValueError(
            f"{field_name} contains characters "
            "that are unsafe for an annotation "
            "artifact filename."
        )


def annotation_artifact_filename(
    annotation: ResponseAnnotation,
) -> str:
    """Return deterministic filename for one annotation."""

    components = (
        (
            "run_id",
            annotation.run_id,
        ),
        (
            "family_id",
            annotation.family_id,
        ),
        (
            "condition",
            annotation.condition.value,
        ),
        (
            "annotator_id",
            annotation.annotator_id,
        ),
    )

    for field_name, value in components:
        _validate_filename_component(
            field_name=field_name,
            value=value,
        )

    return (
        f"{annotation.run_id}_"
        f"{annotation.family_id}_"
        f"{annotation.condition.value}_"
        f"{annotation.annotator_id}.json"
    )


def annotation_output_path(
    *,
    output_directory: Path,
    annotation: ResponseAnnotation,
) -> Path:
    """Return the output path for one annotation."""

    return (
        output_directory
        / annotation_artifact_filename(
            annotation
        )
    )


def write_human_scored_response_artifact_atomic(
    *,
    path: Path,
    payload: dict[str, object],
    overwrite: bool = False,
) -> None:
    """Write one annotation artifact without silent overwrite."""

    if path.exists() and not overwrite:
        raise FileExistsError(
            "Annotation artifact already exists: "
            f"{path}"
        )

    write_raw_results_atomic(
        path=path,
        payload=payload,
    )