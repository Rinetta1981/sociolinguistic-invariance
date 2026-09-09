import pytest

from sociolinguistic_invariance.core import (
    PromptVariant,
    SemanticFamily,
    VariationCondition,
)


def test_semantic_family_accepts_matched_variants() -> None:
    family = SemanticFamily(
        family_id="FP_001",
        task_type="false_premise_correction",
        proposition="Athens is the capital of Italy.",
        variants=(
            PromptVariant(
                condition=VariationCondition.STANDARD,
                text="Η Αθήνα είναι η πρωτεύουσα της Ιταλίας. Γιατί;",
            ),
            PromptVariant(
                condition=VariationCondition.FORMAL,
                text="Θα μπορούσατε να εξηγήσετε γιατί η Αθήνα είναι η πρωτεύουσα της Ιταλίας;",
            ),
        ),
    )

    assert family.family_id == "FP_001"
    assert len(family.variants) == 2


def test_prompt_variant_rejects_empty_text() -> None:
    with pytest.raises(ValueError, match="text must not be empty"):
        PromptVariant(
            condition=VariationCondition.STANDARD,
            text="   ",
        )


def test_semantic_family_rejects_duplicate_conditions() -> None:
    with pytest.raises(ValueError, match="duplicate conditions"):
        SemanticFamily(
            family_id="FP_002",
            task_type="false_premise_correction",
            proposition="Example proposition.",
            variants=(
                PromptVariant(
                    condition=VariationCondition.FORMAL,
                    text="Variant one",
                ),
                PromptVariant(
                    condition=VariationCondition.FORMAL,
                    text="Variant two",
                ),
            ),
        )