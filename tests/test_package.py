import pytest

from sociolinguistic_invariance.core import (
    BenchmarkSplit,
    PromptVariant,
    SemanticFamily,
    TaskType,
    ValidationStatus,
    VariationCondition,
)


def test_semantic_family_accepts_matched_draft_variants() -> None:
    family = SemanticFamily(
        family_id="FP_0001",
        task_type=TaskType.FALSE_PREMISE_CORRECTION,
        proposition="Athens is the capital of Italy.",
        domain="geography",
        split=BenchmarkSplit.DISCOVERY,
        expected_behavior="Correct the false premise.",
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

    assert family.family_id == "FP_0001"
    assert family.task_type is TaskType.FALSE_PREMISE_CORRECTION
    assert family.split is BenchmarkSplit.DISCOVERY
    assert family.validation_status is ValidationStatus.DRAFT
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
            family_id="FP_0002",
            task_type=TaskType.FALSE_PREMISE_CORRECTION,
            proposition="Example proposition.",
            domain="geography",
            split=BenchmarkSplit.DISCOVERY,
            expected_behavior="Correct the false premise.",
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


def test_frozen_family_requires_all_four_conditions() -> None:
    with pytest.raises(ValueError, match="all four benchmark conditions"):
        SemanticFamily(
            family_id="FP_0003",
            task_type=TaskType.FALSE_PREMISE_CORRECTION,
            proposition="Example proposition.",
            domain="geography",
            split=BenchmarkSplit.REPLICATION,
            expected_behavior="Correct the false premise.",
            variants=(
                PromptVariant(
                    condition=VariationCondition.STANDARD,
                    text="Standard version",
                ),
                PromptVariant(
                    condition=VariationCondition.FORMAL,
                    text="Formal version",
                ),
            ),
            validation_status=ValidationStatus.FROZEN,
        )


def test_frozen_family_accepts_complete_condition_set() -> None:
    family = SemanticFamily(
        family_id="FP_0004",
        task_type=TaskType.FALSE_PREMISE_CORRECTION,
        proposition="Example proposition.",
        domain="geography",
        split=BenchmarkSplit.REPLICATION,
        expected_behavior="Correct the false premise.",
        variants=(
            PromptVariant(
                condition=VariationCondition.STANDARD,
                text="Standard version",
            ),
            PromptVariant(
                condition=VariationCondition.FORMAL,
                text="Formal version",
            ),
            PromptVariant(
                condition=VariationCondition.INFORMAL,
                text="Informal version",
            ),
            PromptVariant(
                condition=VariationCondition.GREEKLISH,
                text="Greeklish version",
            ),
        ),
        validation_status=ValidationStatus.FROZEN,
    )

    assert family.validation_status is ValidationStatus.FROZEN
    assert {variant.condition for variant in family.variants} == set(VariationCondition)