from sociolinguistic_invariance.core import (
    BenchmarkSplit,
    PromptVariant,
    SemanticFamily,
    TaskType,
    ValidationStatus,
    VariationCondition,
)
from sociolinguistic_invariance.greeklish import controlled_greeklish


def build_draft_semantic_family(
    *,
    family_id: str,
    task_type: TaskType,
    proposition: str,
    domain: str,
    split: BenchmarkSplit,
    expected_behavior: str,
    standard_text: str,
    formal_text: str,
    informal_text: str,
) -> SemanticFamily:
    """Build a draft semantic family and derive Greeklish from Standard Greek."""

    greeklish_text = controlled_greeklish(standard_text)

    return SemanticFamily(
        family_id=family_id,
        task_type=task_type,
        proposition=proposition,
        domain=domain,
        split=split,
        expected_behavior=expected_behavior,
        variants=(
            PromptVariant(
                condition=VariationCondition.STANDARD,
                text=standard_text,
            ),
            PromptVariant(
                condition=VariationCondition.FORMAL,
                text=formal_text,
            ),
            PromptVariant(
                condition=VariationCondition.INFORMAL,
                text=informal_text,
            ),
            PromptVariant(
                condition=VariationCondition.GREEKLISH,
                text=greeklish_text,
            ),
        ),
        validation_status=ValidationStatus.DRAFT,
    )