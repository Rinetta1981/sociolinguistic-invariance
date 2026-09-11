import hashlib
import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Final

from sociolinguistic_invariance.core import (
    TaskType,
    VariationCondition,
)

ANNOTATION_PROTOCOL_VERSION: Final = (
    "annotation-protocol-v0.1"
)

_SHA256_PATTERN: Final = re.compile(
    r"^[0-9a-f]{64}$"
)


class AnnotationDecision(StrEnum):
    """Human judgment about one annotation criterion."""

    YES = "YES"
    NO = "NO"
    UNCLEAR = "UNCLEAR"


@dataclass(frozen=True, slots=True)
class CriterionAnnotation:
    """One criterion-level judgment for one response."""

    criterion_id: str
    decision: AnnotationDecision
    rationale: str | None = None
    evidence: str | None = None

    def __post_init__(self) -> None:
        """Validate one criterion annotation."""

        if not self.criterion_id.strip():
            raise ValueError(
                "criterion_id must be non-blank."
            )

        if (
            self.rationale is not None
            and not self.rationale.strip()
        ):
            raise ValueError(
                "rationale must be non-blank "
                "when provided."
            )

        if (
            self.evidence is not None
            and not self.evidence.strip()
        ):
            raise ValueError(
                "evidence must be non-blank "
                "when provided."
            )

        if (
            self.decision
            is AnnotationDecision.UNCLEAR
            and self.rationale is None
        ):
            raise ValueError(
                "UNCLEAR criterion annotations "
                "require a rationale."
            )


@dataclass(frozen=True, slots=True)
class ResponseAnnotation:
    """Auditable annotation record for one model response."""

    run_id: str
    request_id: str
    family_id: str
    task_type: TaskType
    condition: VariationCondition
    response_sha256: str
    rubric_version: str
    annotator_id: str
    created_at: datetime
    criteria: tuple[
        CriterionAnnotation,
        ...
    ]
    annotation_protocol_version: str = (
        ANNOTATION_PROTOCOL_VERSION
    )

    def __post_init__(self) -> None:
        """Validate the response annotation."""

        required_strings = (
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
                "rubric_version",
                self.rubric_version,
            ),
            (
                "annotator_id",
                self.annotator_id,
            ),
            (
                "annotation_protocol_version",
                self.annotation_protocol_version,
            ),
        )

        for field_name, value in required_strings:
            if not value.strip():
                raise ValueError(
                    f"{field_name} must be non-blank."
                )

        if not _SHA256_PATTERN.fullmatch(
            self.response_sha256
        ):
            raise ValueError(
                "response_sha256 must be a "
                "64-character lowercase "
                "hexadecimal SHA-256 digest."
            )

        if (
            self.created_at.tzinfo is None
            or self.created_at.utcoffset()
            is None
        ):
            raise ValueError(
                "created_at must be "
                "timezone-aware."
            )

        if not self.criteria:
            raise ValueError(
                "Response annotation must contain "
                "at least one criterion."
            )

        criterion_ids = [
            criterion.criterion_id
            for criterion in self.criteria
        ]

        if len(criterion_ids) != len(
            set(criterion_ids)
        ):
            raise ValueError(
                "Response annotation contains "
                "duplicate criterion_id values."
            )

    @property
    def criterion_count(self) -> int:
        """Return the number of annotated criteria."""

        return len(
            self.criteria
        )

    @property
    def decision_counts(
        self,
    ) -> dict[str, int]:
        """Count criterion decisions deterministically."""

        counts = {
            decision.value: 0
            for decision in AnnotationDecision
        }

        for criterion in self.criteria:
            counts[
                criterion.decision.value
            ] += 1

        return counts


def sha256_response_text(
    response_text: str,
) -> str:
    """Return the SHA-256 identity of exact response text."""

    return hashlib.sha256(
        response_text.encode(
            "utf-8"
        )
    ).hexdigest()


def criterion_annotation_to_dict(
    annotation: CriterionAnnotation,
) -> dict[str, object]:
    """Serialize one criterion annotation."""

    return {
        "criterion_id": annotation.criterion_id,
        "decision": annotation.decision.value,
        "rationale": annotation.rationale,
        "evidence": annotation.evidence,
    }


def response_annotation_to_dict(
    annotation: ResponseAnnotation,
) -> dict[str, object]:
    """Serialize one complete response annotation."""

    return {
        "annotation_protocol_version": (
            annotation.annotation_protocol_version
        ),
        "rubric_version": (
            annotation.rubric_version
        ),
        "run_id": annotation.run_id,
        "request_id": annotation.request_id,
        "family_id": annotation.family_id,
        "task_type": annotation.task_type.value,
        "condition": annotation.condition.value,
        "response_sha256": (
            annotation.response_sha256
        ),
        "annotator_id": annotation.annotator_id,
        "created_at": (
            annotation.created_at.isoformat()
        ),
        "criterion_count": (
            annotation.criterion_count
        ),
        "decision_counts": (
            annotation.decision_counts
        ),
        "criteria": [
            criterion_annotation_to_dict(
                criterion
            )
            for criterion in annotation.criteria
        ],
    }