from dataclasses import dataclass
from enum import StrEnum


class VariationCondition(StrEnum):
    """Sociolinguistic conditions used in the first benchmark."""

    STANDARD = "standard"
    FORMAL = "formal"
    INFORMAL = "informal"
    GREEKLISH = "greeklish"


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
    """Matched prompt variants intended to preserve the same underlying meaning."""

    family_id: str
    task_type: str
    proposition: str
    variants: tuple[PromptVariant, ...]

    def __post_init__(self) -> None:
        if not self.family_id.strip():
            raise ValueError("family_id must not be empty")

        if not self.task_type.strip():
            raise ValueError("task_type must not be empty")

        if not self.proposition.strip():
            raise ValueError("proposition must not be empty")

        if len(self.variants) < 2:
            raise ValueError("a semantic family must contain at least two variants")

        conditions = [variant.condition for variant in self.variants]

        if len(set(conditions)) != len(conditions):
            raise ValueError("a semantic family cannot contain duplicate conditions")