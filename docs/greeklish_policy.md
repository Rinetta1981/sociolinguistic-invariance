# Controlled Greeklish Policy — Benchmark v0.1

## Status

This document defines the Greeklish transformation used in version 0.1 of the
Sociolinguistic Invariance benchmark.

The policy must be fixed before construction of the confirmatory benchmark.

---

## 1. Purpose

Greeklish has no single standardized orthography.

Naturally occurring Greeklish may vary according to:

- writer;
- platform;
- period;
- phonetic preference;
- orthographic preference;
- abbreviations;
- slang;
- numerical substitutions;
- code-switching.

Version 0.1 does not attempt to represent the full sociolinguistic diversity of
natural Greeklish.

Instead, it uses **Controlled Greeklish** as an experimental condition designed
to isolate Latin-script representation of Greek as far as practically possible.

Naturalistic Greeklish will be treated as a separate future benchmark module.

---

## 2. Experimental principle

For every semantic family:

    Standard Modern Greek
            ↓
    deterministic transliteration
            ↓
    Controlled Greeklish

The Greeklish prompt must not be independently rewritten.

This means that the Greeklish condition should preserve, as far as possible:

- lexical choice;
- word order;
- syntax;
- sentence boundaries;
- punctuation;
- requested action;
- propositional content.

The intended manipulated variable is primarily script and orthographic
representation.

---

## 3. Transliteration style

Version 0.1 uses an orthography-oriented, deterministic Latin transliteration.

It does not attempt to reproduce pronunciation precisely.

The same Greek character should normally receive the same Latin representation
regardless of context.

The core lowercase mapping is:

| Greek | Controlled Greeklish |
|---|---|
| α | a |
| β | v |
| γ | g |
| δ | d |
| ε | e |
| ζ | z |
| η | i |
| θ | th |
| ι | i |
| κ | k |
| λ | l |
| μ | m |
| ν | n |
| ξ | x |
| ο | o |
| π | p |
| ρ | r |
| σ | s |
| ς | s |
| τ | t |
| υ | y |
| φ | f |
| χ | ch |
| ψ | ps |
| ω | o |

### Uppercase convention

Uppercase Greek characters follow the corresponding Latin capitalization.

For mappings containing more than one Latin character, only the first Latin
character is capitalized:

    Θ → Th
    Χ → Ch
    Ψ → Ps

The corresponding lowercase mappings remain:

    θ → th
    χ → ch
    ψ → ps

Single-character uppercase mappings follow the corresponding uppercase Latin
form, for example:

    Α → A
    Β → V
    Γ → G
    Δ → D
    Η → I
    Σ → S
    Ω → O

This convention is deterministic and is intended to improve readability without
introducing phonological interpretation.

For example:

    Θέλω
        ↓
    Thelo

rather than:

    THelo

---

## 4. Accents and diacritics

Greek tonos and diaeresis marks are removed during Controlled Greeklish
transliteration.

Examples:

    ά → a
    έ → e
    ή → i
    ί → i
    ό → o
    ύ → y
    ώ → o
    ϊ → i
    ϋ → y

This choice is part of the predefined v0.1 intervention and must be applied
consistently.

The absence of accent marks is therefore not to be interpreted separately from
the Controlled Greeklish condition in v0.1.

Diacritics belonging to existing non-Greek Latin-script material should remain
unchanged.

For example:

    café
        ↓
    café

not:

    cafe

---

## 5. Digraphs and character sequences

Version 0.1 primarily uses character-level transliteration.

Greek character sequences are not automatically replaced with phonetic
equivalents.

For example:

    ου
        ↓
    oy

and:

    μπ
        ↓
    mp

The system should not independently decide that these sequences should be
rewritten according to their pronunciation.

This protects against introducing an additional phonetic-normalization
intervention.

Any exceptional rule introduced later must be documented and versioned.

---

## 6. Numbers

Numbers remain unchanged.

Example:

    3 βιβλία
        ↓
    3 vivlia

Numbers must not be used as Greek-character substitutes.

Therefore forms such as:

    8elo

for:

    θέλω

are outside the Controlled Greeklish condition in v0.1.

They may be investigated in a future naturalistic Greeklish module.

---

## 7. Punctuation

Punctuation should be preserved wherever technically possible.

The transliteration process must not deliberately alter:

- question status;
- sentence boundaries;
- quotation structure;
- enumeration;
- emphasis.

Example:

    Θέλω 3 βιβλία;
        ↓
    Thelo 3 vivlia;

Any automatic punctuation normalization must be documented.

---

## 8. Latin material already present in the prompt

Existing Latin-script material should normally remain unchanged.

Examples include:

- URLs;
- acronyms;
- model names;
- technical terms already written in Latin characters;
- Latin-script words containing diacritics.

For example:

    AI και café
        ↓
    AI kai café

The transliterator must not attempt to retransliterate or normalize such
material.

---

## 9. Proper names

Greek-script proper names are transliterated according to the same controlled
mapping unless an item-specific reason requires otherwise.

A conventional English exonym must not silently replace the Greek proper name.

For example, transliteration and translation are treated as different
operations.

Any exception must be documented in item metadata.

---

## 10. No additional informalization

Controlled Greeklish must not automatically introduce:

- slang;
- abbreviations;
- emojis;
- omitted words;
- shortened syntax;
- phonetic spelling;
- numerical substitutions;
- repeated letters;
- internet discourse markers.

These features are sociolinguistically interesting but would create additional
experimental manipulations.

---

## 11. Human inspection

Every automatically generated Controlled Greeklish variant must receive human
inspection before a semantic family can be frozen.

Inspection should check:

- transliteration completeness;
- accidental untranslated Greek characters;
- readability;
- punctuation preservation;
- accidental semantic change;
- accidental lexical replacement;
- proper-name handling;
- preservation of existing Latin-script material.

Automatic transliteration alone does not constitute benchmark validation.

---

## 12. Metadata

Each Greeklish variant should ultimately be associated with metadata identifying
the transformation policy.

The initial policy identifier is:

    controlled-greeklish-v0.1

This identifier must correspond to the implementation used to generate the
variant.

This allows future benchmark releases to distinguish this condition from other
Greeklish conventions.

---

## 13. Claim boundary

A result involving Controlled Greeklish supports a claim about model behavior
under this specified Latin-script transformation.

It does not by itself support a claim about:

- all Greeklish users;
- naturally occurring Greeklish;
- youth language;
- digital literacy;
- education;
- social class;
- diaspora Greek;
- individual speaker identity.

Controlled Greeklish is an experimental intervention, not a demographic proxy.

---

## 14. Future naturalistic Greeklish module

A later benchmark version may include naturally occurring or human-authored
Greeklish.

Such a module may investigate variation including:

- phonetic spellings;
- orthographic spellings;
- numerical substitution;
- abbreviations;
- slang;
- platform-specific conventions;
- code-switching.

That module will require its own sampling, annotation, validation, and
preregistration protocol.

It will not be silently combined with Controlled Greeklish v0.1.