from dataclasses import dataclass
from enum import StrEnum


class VariationCondition(StrEnum):
    """Sociolinguistic conditions used in benchmark version 0.1."""

    STANDARD = "standard"
    FORMAL = "formal"
    INFORMAL = "informal"
    GREEKLISH = "greeklish"


class TaskType(StrEnum):
    """Confirmatory task types used in benchmark version 0.1."""

    FALSE_PREMISE_CORRECTION = "false_premise_correction"
    EPISTEMIC_UNCERTAINTY = "epistemic_uncertainty"
    BENIGN_REQUEST = "benign_request"


class BenchmarkSplit(StrEnum):
    """Independent benchmark partitions."""

    DISCOVERY = "discovery"
    REPLICATION = "replication"


class ValidationStatus(StrEnum):
    """Lifecycle state of a semantic family."""

    DRAFT = "draft"
    REVIEWED = "reviewed"
    FROZEN = "frozen"
    EXCLUDED = "excluded"


@dataclass(frozen=True, slots=True)
class PromptVariant:
    """One linguistic realization of an underlying semantic task."""

    condition: VariationCondition
    text: str

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("text must not be empty")


@dataclass(frozen=True, slots=True)
class SemanticFamily:
    """Matched variants intended to preserve the same substantive task."""

    family_id: str
    task_type: TaskType
    proposition: str
    domain: str
    split: BenchmarkSplit
    expected_behavior: str
    variants: tuple[PromptVariant, ...]
    validation_status: ValidationStatus = ValidationStatus.DRAFT

    def __post_init__(self) -> None:
        if not self.family_id.strip():
            raise ValueError("family_id must not be empty")

        if not self.proposition.strip():
            raise ValueError("proposition must not be empty")

        if not self.domain.strip():
            raise ValueError("domain must not be empty")

        if not self.expected_behavior.strip():
            raise ValueError("expected_behavior must not be empty")

        if len(self.variants) < 2:
            raise ValueError("a semantic family must contain at least two variants")

        conditions = [variant.condition for variant in self.variants]

        if len(set(conditions)) != len(conditions):
            raise ValueError("a semantic family cannot contain duplicate conditions")

        if self.validation_status is ValidationStatus.FROZEN:
            required_conditions = set(VariationCondition)
            actual_conditions = set(conditions)

            if actual_conditions != required_conditions:
                raise ValueError(
                    "a frozen semantic family must contain all four benchmark conditions"
                )