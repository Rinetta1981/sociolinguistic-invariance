from unicodedata import combining, normalize

CONTROLLED_GREEKLISH_POLICY_ID = "controlled-greeklish-v0.1"


_GREEK_TO_LATIN: dict[str, str] = {
    "α": "a",
    "β": "v",
    "γ": "g",
    "δ": "d",
    "ε": "e",
    "ζ": "z",
    "η": "i",
    "θ": "th",
    "ι": "i",
    "κ": "k",
    "λ": "l",
    "μ": "m",
    "ν": "n",
    "ξ": "x",
    "ο": "o",
    "π": "p",
    "ρ": "r",
    "σ": "s",
    "ς": "s",
    "τ": "t",
    "υ": "y",
    "φ": "f",
    "χ": "ch",
    "ψ": "ps",
    "ω": "o",
    "Α": "A",
    "Β": "V",
    "Γ": "G",
    "Δ": "D",
    "Ε": "E",
    "Ζ": "Z",
    "Η": "I",
    "Θ": "Th",
    "Ι": "I",
    "Κ": "K",
    "Λ": "L",
    "Μ": "M",
    "Ν": "N",
    "Ξ": "X",
    "Ο": "O",
    "Π": "P",
    "Ρ": "R",
    "Σ": "S",
    "Τ": "T",
    "Υ": "Y",
    "Φ": "F",
    "Χ": "Ch",
    "Ψ": "Ps",
    "Ω": "O",
}


def controlled_greeklish(text: str) -> str:
    """Transliterate Greek using the Controlled Greeklish v0.1 policy."""

    normalized_text = normalize("NFD", text)
    output: list[str] = []
    previous_character_was_greek = False

    for character in normalized_text:
        if combining(character):
            if previous_character_was_greek:
                continue

            output.append(character)
            continue

        replacement = _GREEK_TO_LATIN.get(character)

        if replacement is not None:
            output.append(replacement)
            previous_character_was_greek = True
        else:
            output.append(character)
            previous_character_was_greek = False

    return normalize("NFC", "".join(output))