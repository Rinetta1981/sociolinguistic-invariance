from dataclasses import dataclass, replace

from sociolinguistic_invariance.core import (
    PromptVariant,
    SemanticFamily,
    ValidationStatus,
    VariationCondition,
)
from sociolinguistic_invariance.greeklish import controlled_greeklish


@dataclass(frozen=True, slots=True)
class ReviewChecklist:
    """Human review evidence required before a family can be marked reviewed."""

    reviewer_id: str
    semantic_equivalence: bool
    sociolinguistic_naturalness: bool
    factual_content_preserved: bool
    expected_behavior_clear: bool
    no_prohibited_confounds: bool
    greeklish_verified: bool
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.reviewer_id.strip():
            raise ValueError("reviewer_id must not be empty")

    @property
    def all_checks_passed(self) -> bool:
        """Return whether every required human-review check passed."""

        return all(
            (
                self.semantic_equivalence,
                self.sociolinguistic_naturalness,
                self.factual_content_preserved,
                self.expected_behavior_clear,
                self.no_prohibited_confounds,
                self.greeklish_verified,
            )
        )


def _variant_map(
    family: SemanticFamily,
) -> dict[VariationCondition, PromptVariant]:
    """Return variants indexed by sociolinguistic condition."""

    return {variant.condition: variant for variant in family.variants}


def _require_complete_condition_set(family: SemanticFamily) -> None:
    """Require all four v0.1 benchmark conditions."""

    conditions = {variant.condition for variant in family.variants}

    if conditions != set(VariationCondition):
        raise ValueError(
            "review requires all four benchmark conditions"
        )


def _require_controlled_greeklish(family: SemanticFamily) -> None:
    """Require Greeklish to match deterministic transliteration of Standard."""

    variants = _variant_map(family)

    standard_text = variants[VariationCondition.STANDARD].text
    greeklish_text = variants[VariationCondition.GREEKLISH].text

    expected_greeklish = controlled_greeklish(standard_text)

    if greeklish_text != expected_greeklish:
        raise ValueError(
            "Greeklish variant does not match Controlled Greeklish policy"
        )


def mark_reviewed(
    family: SemanticFamily,
    checklist: ReviewChecklist,
) -> SemanticFamily:
    """Move a draft family to reviewed after all required checks pass."""

    if family.validation_status is not ValidationStatus.DRAFT:
        raise ValueError("only draft families can be marked reviewed")

    _require_complete_condition_set(family)
    _require_controlled_greeklish(family)

    if not checklist.all_checks_passed:
        raise ValueError("all required human-review checks must pass")

    return replace(
        family,
        validation_status=ValidationStatus.REVIEWED,
    )


def freeze_family(family: SemanticFamily) -> SemanticFamily:
    """Freeze a reviewed family after final machine-verifiable checks."""

    if family.validation_status is not ValidationStatus.REVIEWED:
        raise ValueError("only reviewed families can be frozen")

    _require_complete_condition_set(family)
    _require_controlled_greeklish(family)

    return replace(
        family,
        validation_status=ValidationStatus.FROZEN,
    )