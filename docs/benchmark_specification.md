# Benchmark Specification: Sociolinguistic Invariance v0.1

## Status

This document defines the construction and validation rules for version 0.1 of
the Sociolinguistic Invariance benchmark.

It should be read together with `preregistration.md`.

The benchmark is designed to test language-model behavior under controlled
within-language sociolinguistic variation while preserving semantic content and
task demands.

Greek is the first testbed.

---

## 1. Scope of version 0.1

Version 0.1 contains four conditions:

1. Standard Modern Greek
2. formal/institutional Greek
3. informal/colloquial Greek
4. Greeklish

The first three conditions manipulate register.

The Greeklish condition primarily manipulates writing system and orthographic
presentation.

Dialectal, regional, heritage, and diaspora varieties are excluded from v0.1.
They require additional community or expert validation and will be introduced
only in later benchmark versions.

---

## 2. Unit of construction

The fundamental benchmark object is the **semantic family**.

Each semantic family represents one underlying communicative task and contains
multiple sociolinguistic realizations of that task.

A valid family must preserve across variants:

- the underlying proposition;
- the requested action;
- the relevant factual information;
- the intended referents;
- the epistemic status of the proposition;
- the safety status of the request;
- the practical difficulty of answering.

Only sociolinguistically relevant surface realization may change.

---

## 3. Variant conditions

### 3.1 Standard Modern Greek

The Standard condition should use contemporary, neutral written Standard Modern
Greek.

It should:

- follow conventional Greek orthography;
- avoid conspicuously formal or bureaucratic wording;
- avoid marked slang;
- avoid regionally restricted forms;
- avoid unnecessarily elaborate syntax;
- sound natural in an ordinary contemporary written interaction.

The Standard condition serves as the principal comparison condition.

---

### 3.2 Formal/institutional Greek

The Formal condition should preserve the same task while increasing register
formality.

Permitted changes include:

- polite address;
- more formal lexical choices;
- institutional or professional phrasing;
- greater syntactic elaboration where natural;
- conventional mitigation;
- impersonal constructions where appropriate.

The Formal condition must not:

- add credentials or claims of authority;
- imply that the speaker is an expert;
- introduce institutional evidence;
- make the proposition sound more factually supported;
- add urgency, threat, status, or power;
- change the requested action.

Formality must therefore be encoded linguistically rather than by adding social
facts about the speaker.

---

### 3.3 Informal/colloquial Greek

The Informal condition should preserve the same task while using natural,
contemporary conversational Greek.

Permitted changes include:

- conversational syntax;
- ordinary colloquial vocabulary;
- reduced formality;
- discourse markers where they do not change meaning;
- direct forms of request that remain pragmatically comparable.

The Informal condition must not:

- become aggressive or insulting;
- imply low education or intelligence;
- add emotional pressure;
- change certainty or evidential stance;
- introduce new factual information;
- alter the requested action.

Informality must not be operationalized as caricature.

---

### 3.4 Greeklish

The Greeklish condition tests the effect of Latin-script representation of
Greek.

For v0.1, Greeklish should be derived from the Standard Modern Greek condition
rather than from the Informal condition.

The goal is to isolate orthographic/script variation as far as practical.

The Greeklish version must preserve:

- lexical choices;
- syntax;
- sentence order;
- proposition;
- requested action;
- punctuation where practical.

A documented transliteration convention will be used consistently across the
benchmark.

Every automatically transliterated item must receive manual inspection for
readability and accidental ambiguity.

Naturalistic Greeklish involving simultaneous slang or register changes is
outside the confirmatory scope of v0.1.

---

## 4. What may and may not vary

### Permitted variation

Across register conditions, the following may change where necessary to produce
a natural realization:

- lexical formality;
- politeness;
- conversational markers;
- syntactic formality;
- forms of address;
- discourse style.

### Variables intended to remain invariant

The following must remain substantively constant:

- propositional content;
- factual information;
- task;
- target of the request;
- answerability;
- epistemic evidence;
- safety status;
- intended meaning.

If a natural register transformation cannot be produced without altering one of
these properties, that semantic family must be revised or excluded.

---

## 5. Prohibited confounds

Variants must not differ systematically in:

- speaker credentials;
- explicit education level;
- occupation;
- socioeconomic status;
- nationality;
- ethnicity;
- gender;
- age;
- political identity;
- emotional threat;
- urgency;
- number of factual claims;
- amount of evidence supplied.

The benchmark evaluates linguistic form.

It is not designed to test explicit demographic descriptions of users.

---

## 6. Initial task types

### 6.1 False-premise correction

Each family contains a clearly false factual premise.

The falsehood must be:

- verifiable;
- unambiguous;
- non-time-sensitive;
- unrelated to high-stakes medical, legal, or financial advice;
- expressible naturally in all benchmark conditions.

The expected substantive behavior is correction or clear rejection of the false
premise.

The benchmark tests whether correction behavior changes across sociolinguistic
conditions.

---

### 6.2 Epistemic uncertainty

Each family contains a question for which the supplied evidence does not justify
a fully certain answer.

The underdetermination must arise from the information available in the task,
not from obscure specialist knowledge.

The benchmark tests whether model certainty changes when evidential conditions
remain constant but linguistic realization changes.

---

### 6.3 Benign request handling

Each family contains a harmless and normally answerable request.

Items should avoid:

- safety-sensitive content;
- ambiguous harmful intent;
- legal or medical risk;
- personal data;
- controversial policy edge cases.

The benchmark tests whether refusal, excessive caution, or avoidance differs
across linguistic conditions.

---

## 7. Domain balance

Semantic families should be drawn from multiple low-risk domains so that an
effect cannot easily be attributed to one narrow content area.

Candidate domains include:

- everyday factual knowledge;
- geography;
- basic science;
- cultural knowledge;
- ordinary reasoning;
- non-sensitive practical tasks.

Current events and rapidly changing facts should normally be excluded from the
confirmatory benchmark.

Domain composition will be recorded in benchmark metadata.

---

## 8. Semantic family identifiers

Identifiers should encode task type but not sociolinguistic condition.

Recommended prefixes:

    FP = false-premise correction
    EU = epistemic uncertainty
    BR = benign request

Examples:

    FP_0001
    FP_0002
    EU_0001
    BR_0001

The same `family_id` is shared by all variants belonging to one semantic family.

Condition is stored separately.

---

## 9. Benchmark record structure

The canonical dataset representation will be structured rather than stored only
as free text.

A semantic family should contain at least:

    family_id
    task_type
    proposition
    domain
    split
    expected_behavior
    variants
    validation_status

Each variant should contain:

    condition
    text

Additional metadata may include:

    notes
    construction_source
    reviewer_status
    transliteration_policy
    exclusion_reason

The canonical frozen representation will be machine-readable.

JSON Lines is the preferred initial format because one semantic family can be
stored as one structured record while preserving nested variants.

---

## 10. Illustrative schema

The following is a structural illustration only and is not benchmark data:

    {
      "family_id": "FP_XXXX",
      "task_type": "false_premise_correction",
      "proposition": "<shared proposition>",
      "domain": "<domain>",
      "split": "<discovery-or-replication>",
      "expected_behavior": "<prespecified expected behavior>",
      "variants": [
        {
          "condition": "standard",
          "text": "<standard Greek version>"
        },
        {
          "condition": "formal",
          "text": "<formal Greek version>"
        },
        {
          "condition": "informal",
          "text": "<informal Greek version>"
        },
        {
          "condition": "greeklish",
          "text": "<Greeklish version>"
        }
      ],
      "validation_status": "<status>"
    }

---

## 11. Construction workflow

Each semantic family should pass through the following stages:

    draft proposition
        ↓
    construct Standard version
        ↓
    construct Formal and Informal variants
        ↓
    construct Greeklish from Standard
        ↓
    semantic-equivalence review
        ↓
    sociolinguistic-naturalness review
        ↓
    metadata completion
        ↓
    split assignment
        ↓
    freeze

No confirmatory model call should be made on a family before the family has
passed the required validation stage.

---

## 12. Semantic-equivalence review

Each family must be checked explicitly for whether all variants preserve:

- proposition;
- requested action;
- referents;
- factual content;
- epistemic stance required by the task;
- safety status.

Reviewers should ask:

> If these prompts were stripped of their register and orthographic differences,
> would a reasonable evaluator regard them as requesting the same substantive
> response?

If not, the family must be revised.

---

## 13. Sociolinguistic-naturalness review

A formally correct transformation is not sufficient.

Each condition should also sound like a plausible linguistic realization rather
than a mechanical substitution exercise.

Review should consider:

- lexical naturalness;
- syntax;
- pragmatic coherence;
- degree of register marking;
- absence of parody or stereotyping.

Automatic generation may assist drafting, but automatic generation alone does
not constitute linguistic validation.

---

## 14. Human validation

Confirmatory items require human linguistic review.

At minimum, every item must receive deliberate human inspection before freezing.

A stratified subset should receive independent second-person review where
practically possible.

Agreement and disagreement during validation should be documented rather than
silently resolved.

Future dialectal modules will require stronger community or specialist
validation than the v0.1 register benchmark.

---

## 15. Discovery and replication integrity

Discovery and replication sets must contain different semantic families.

A proposition used in discovery must not be lightly paraphrased and reused in
replication.

Near-duplicate semantic content should be assigned to the same split or removed.

Replication items must remain unavailable for hypothesis refinement until the
discovery analysis is complete.

---

## 16. Data freezing

Before confirmatory model evaluation, the benchmark version will be frozen.

The frozen release should record:

- benchmark version;
- creation date;
- number of semantic families;
- number of variants;
- split composition;
- validation status;
- file hash or manifest.

Frozen benchmark records must not be silently edited after model outputs are
collected.

Corrections require a new benchmark version or a documented amendment.

---

## 17. Exclusions

A semantic family should be excluded before freezing if:

- variants are not semantically equivalent;
- the intended register sounds unnatural;
- the proposition is factually disputed;
- the expected behavior is unclear;
- the item becomes time-sensitive;
- the answer depends on hidden context;
- the Greeklish rendering creates substantial ambiguity;
- safety classification is uncertain.

Exclusion decisions should be documented.

---

## 18. Claim boundary

Version 0.1 evaluates controlled differences among Standard Modern Greek,
formal/institutional Greek, informal/colloquial Greek, and Greeklish.

Results must not be generalized automatically to:

- all Greek speakers;
- all Greek dialects;
- demographic groups;
- social classes;
- educational groups;
- heritage speakers;
- diaspora communities.

The benchmark measures model sensitivity to specified linguistic forms, not
properties of the people who may use them.

---

## 19. Relationship to future versions

Possible later modules include:

- Cypriot Greek;
- regional Greek varieties;
- diaspora Greek;
- heritage-speaker Greek;
- code-switching;
- naturally occurring Greeklish;
- spoken-language and speech-recognition evaluation.

These extensions require separate validation and versioned research protocols.

They are not part of the confirmatory claims of v0.1.