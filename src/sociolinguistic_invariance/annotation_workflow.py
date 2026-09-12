import re
from collections.abc import Sequence
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

_SAFE_COMPONENT_PATTERN: Final = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9._-]*$"
)


def _require_non_blank_string(
    value: str,
    *,
    field_name: str,
) -> None:
    """Require one non-blank string."""

    if (
        not isinstance(value, str)
        or not value.strip()
    ):
        raise ValueError(
            f"{field_name} must be non-blank."
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AnnotationSource:
    """Immutable source metadata for one response annotation."""

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
        """Validate annotation source metadata."""

        for field_name, value in (
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
        ):
            _require_non_blank_string(
                value,
                field_name=field_name,
            )

        if not isinstance(
            self.source_benchmark_claim_eligible,
            bool,
        ):
            raise TypeError(
                "source_benchmark_claim_eligible "
                "must be a bool."
            )


def _validate_source_binding(
    *,
    source: AnnotationSource,
    scored: ScoredResponseAnnotation,
) -> None:
    """Require scored annotation metadata to match its source."""

    annotation = scored.annotation

    if annotation.run_id != source.run_id:
        raise ValueError(
            "Annotation run_id does not match source."
        )

    if (
        annotation.request_id
        != source.request_id
    ):
        raise ValueError(
            "Annotation request_id does not match source."
        )

    if annotation.family_id != source.family_id:
        raise ValueError(
            "Annotation family_id does not match source."
        )

    if annotation.task_type is not source.task_type:
        raise ValueError(
            "Annotation task_type does not match source."
        )

    if annotation.condition is not source.condition:
        raise ValueError(
            "Annotation condition does not match source."
        )

    expected_response_sha256 = (
        sha256_response_text(
            source.response_text
        )
    )

    if (
        annotation.response_sha256
        != expected_response_sha256
    ):
        raise ValueError(
            "Annotation response_sha256 does not "
            "match source response text."
        )


def create_scored_response_annotation(
    *,
    source: AnnotationSource,
    annotator_id: str,
    criteria: Sequence[
        CriterionAnnotation
    ],
    created_at: datetime,
) -> ScoredResponseAnnotation:
    """Create and deterministically score one human annotation."""

    _require_non_blank_string(
        annotator_id,
        field_name="annotator_id",
    )

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
        criteria=tuple(
            criteria
        ),
    )

    scored = score_response_annotation(
        annotation=annotation,
        response_text=source.response_text,
    )

    _validate_source_binding(
        source=source,
        scored=scored,
    )

    return scored


def human_scored_response_artifact_to_dict(
    *,
    source: AnnotationSource,
    scored: ScoredResponseAnnotation,
    git_provenance: GitProvenance,
) -> dict[str, object]:
    """Serialize one auditable human-scored response artifact."""

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


def _safe_filename_component(
    value: str,
    *,
    field_name: str,
) -> str:
    """Require one safe deterministic filename component."""

    _require_non_blank_string(
        value,
        field_name=field_name,
    )

    if (
        value in {
            ".",
            "..",
        }
        or _SAFE_COMPONENT_PATTERN.fullmatch(
            value
        )
        is None
    ):
        raise ValueError(
            f"{field_name} is unsafe for an annotation "
            "artifact filename."
        )

    return value


def annotation_artifact_filename(
    annotation: ResponseAnnotation,
) -> str:
    """Return the deterministic filename for one annotation."""

    run_id = _safe_filename_component(
        annotation.run_id,
        field_name="run_id",
    )

    family_id = _safe_filename_component(
        annotation.family_id,
        field_name="family_id",
    )

    condition = _safe_filename_component(
        annotation.condition.value,
        field_name="condition",
    )

    annotator_id = _safe_filename_component(
        annotation.annotator_id,
        field_name="annotator_id",
    )

    return (
        f"{run_id}_"
        f"{family_id}_"
        f"{condition}_"
        f"{annotator_id}.json"
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
        overwrite=overwrite,
    )