from sociolinguistic_invariance.greeklish import (
    CONTROLLED_GREEKLISH_POLICY_ID,
    controlled_greeklish,
)


def test_policy_id_is_versioned() -> None:
    assert CONTROLLED_GREEKLISH_POLICY_ID == "controlled-greeklish-v0.1"


def test_transliterates_basic_greek() -> None:
    assert controlled_greeklish("θέλω") == "thelo"


def test_removes_greek_accents_and_diaeresis() -> None:
    assert controlled_greeklish("ά έ ή ί ό ύ ώ ϊ ϋ") == "a e i i o y o i y"


def test_preserves_uppercase_distinction() -> None:
    assert controlled_greeklish("Άνθρωπος") == "Anthropos"


def test_handles_final_sigma() -> None:
    assert controlled_greeklish("κόσμος") == "kosmos"


def test_preserves_numbers_and_punctuation() -> None:
    assert controlled_greeklish("Θέλω 3 βιβλία;") == "Thelo 3 vivlia;"


def test_preserves_existing_latin_text() -> None:
    assert controlled_greeklish("Claude café") == "Claude café"


def test_handles_mixed_greek_and_latin_text() -> None:
    assert controlled_greeklish("AI και café") == "AI kai café"


def test_uses_character_level_mapping_for_sequences() -> None:
    assert controlled_greeklish("ου μπ γγ") == "oy mp gg"


def test_preserves_whitespace() -> None:
    assert controlled_greeklish("δύο   λέξεις") == "dyo   lexeis"