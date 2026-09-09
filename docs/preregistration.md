# Preregistration: Sociolinguistic Invariance v0.1

## Status

This document defines the confirmatory logic for version 0.1 of the
Sociolinguistic Invariance benchmark.

It is written before collection of the main model-response dataset.

Exploratory analyses may be conducted, but exploratory results will not be
reported as confirmatory findings unless they survive the replication procedure
defined below.

---

## 1. Research question

When semantic content and task demands are held constant, does a language
model's substantive behavior change as a function of socially meaningful
linguistic form?

Greek is the first testbed.

Version 0.1 examines:

- Standard Modern Greek
- formal/institutional Greek
- informal/colloquial Greek
- Greeklish

Dialectal and diaspora varieties are outside the confirmatory scope of v0.1 and
will be introduced only after appropriate speaker or expert validation.

---

## 2. Core principle

The project distinguishes linguistic accommodation from substantive behavioral
drift.

### Accommodation may legitimately vary

Examples include:

- vocabulary
- politeness
- degree of formality
- sentence structure
- forms of address
- conversational style
- orthographic conventions where appropriate

### The following should not change merely because sociolinguistic form changes

Where semantic content and task demands are matched:

- factual correctness
- detection and correction of false premises
- evidential standards
- warranted uncertainty
- core safety judgment
- willingness to answer a benign request
- substantive agreement or disagreement with a proposition

The project refers to appropriate stability in these dimensions as
**conditional sociolinguistic invariance**.

---

## 3. Unit of analysis

The primary unit is the **semantic family**.

A semantic family contains multiple prompts designed to preserve:

1. the same underlying proposition;
2. the same task;
3. the same relevant factual information;
4. the same requested action;

while varying sociolinguistic realization.

Each family receives a unique identifier.

Example structure:

    family_id: FP_001
    task_type: false_premise_correction
    proposition: <shared proposition>

    variants:
        standard
        formal
        informal
        greeklish

Prompts used in software tests are not part of the benchmark dataset.

---

## 4. Initial task families

Version 0.1 will begin with three task types.

### 4.1 False-premise correction

The prompt contains a clearly false factual premise.

Primary question:

Does the model identify or correct the false premise consistently across
sociolinguistic conditions?

### 4.2 Epistemic uncertainty

The prompt asks about a proposition for which the available information does
not justify certainty.

Primary question:

Does expressed certainty or uncertainty change systematically across
sociolinguistic conditions without an evidential reason?

### 4.3 Benign request handling

The prompt contains a harmless request that should normally be answerable.

Primary question:

Does refusal, avoidance, or unnecessary restriction differ across
sociolinguistic conditions?

Additional task types may be developed exploratorily but will not become
confirmatory outcomes without a new versioned preregistration.

---

## 5. Primary outcome variables

### 5.1 False-premise correction rate

Binary outcome indicating whether the response clearly identifies or corrects
the false premise.

### 5.2 Unsupported agreement rate

Binary outcome indicating whether the model accepts or reinforces a false or
unsupported proposition presented by the user.

### 5.3 Uncertainty score

Ordinal or continuous measure of warranted uncertainty, using a scoring
procedure defined before confirmatory evaluation.

### 5.4 Benign refusal rate

Binary outcome indicating whether the model refuses or materially avoids a
benign request.

### 5.5 Semantic-content preservation

Measure of whether substantive answer content remains stable across matched
variants after legitimate stylistic accommodation is separated from content.

---

## 6. Discovery and replication split

Semantic families will be divided before confirmatory model evaluation into:

- a **discovery set**
- an independent **replication set**

The replication set must contain different semantic families rather than
rewrites of discovery items.

The replication set will remain unused for hypothesis refinement until the
discovery analysis has been completed.

---

## 7. Replication rule

A sociolinguistic effect will not be treated as robust merely because it is
large or statistically detectable in the discovery set.

For a behavioral effect to justify a strong claim, it must:

1. occur in the prespecified direction or exhibit the same qualitative pattern
   in the independent replication set;
2. remain meaningfully different after accounting for family-level pairing;
3. not depend on a very small number of semantic families;
4. survive the prespecified robustness checks;
5. be distinguishable from legitimate stylistic accommodation.

Failure to replicate will be reported as a null or unstable result rather than
retrofitted into a positive claim.

---

## 8. Statistical principle

Analyses will preserve the matched structure of semantic families.

Primary comparisons will therefore be paired or family-aware rather than
treating every prompt response as independent.

Effect sizes and uncertainty intervals will be reported alongside significance
tests where applicable.

Exact statistical models will be specified before the confirmatory dataset is
evaluated.

---

## 9. Model evaluation principle

The initial benchmark will support more than one model or model family where
practically possible.

Model identity, model version, inference settings, system prompts, temperature,
sampling parameters, and evaluation date will be recorded.

Model outputs will not be silently regenerated or selectively discarded.

Failed API calls and technical exclusions will be logged separately from
behavioral exclusions.

---

## 10. Scoring principle

Where an outcome can be determined programmatically or by explicit rules, that
method will be preferred.

Where human judgment is required:

- the annotation rule will be written before confirmatory scoring;
- ambiguous cases will be represented as such rather than forced into a binary
  label where possible;
- a validation subset will receive independent human review.

LLM-as-judge scoring may be used as a supplementary tool but will not be treated
as unquestioned ground truth.

---

## 11. Linguistic validity

The sociolinguistic manipulation must not unintentionally change the underlying
task.

Each semantic family must therefore be checked for:

- propositional equivalence;
- task equivalence;
- absence of added factual information;
- absence of removed factual information;
- naturalness of the intended condition.

Greeklish is treated as an orthographic/socially meaningful condition and not
as a separate language.

Dialectal varieties will not be added merely through unvalidated automatic
translation or LLM generation.

---

## 12. Interpretability gate

Mechanistic or representation-level interpretation is conditional on robust
behavioral replication.

The project will not proceed from an exploratory behavioral difference directly
to a mechanistic explanation.

The sequence is:

    discovery
        ↓
    candidate behavioral effect
        ↓
    independent replication
        ↓
    robustness analysis
        ↓
    mechanistic investigation, if justified

If the behavioral effect fails to replicate, the null or instability result is
retained and reported.

---

## 13. Stopping rule

For a prespecified hypothesis, confirmatory interpretation stops if:

- the discovery effect fails to replicate;
- the direction of effect reverses materially;
- the effect is attributable to semantic mismatch between variants;
- annotation reliability is inadequate;
- technical artifacts explain the apparent difference.

A failed gate is an outcome of the research, not a reason to redesign the test
until a positive result appears.

---

## 14. Research ethics and representation

The project evaluates model behavior toward linguistic forms; it does not infer
a speaker's identity from language.

The benchmark will not treat register, Greeklish, dialect, or other forms as
reliable proxies for:

- ethnicity
- class
- education
- gender
- nationality
- intelligence
- moral character

Future work involving recordings, dialect communities, or participant data will
require an additional documented consent and governance protocol.

---

## 15. Versioning

This document governs benchmark version 0.1.

Any substantive change to:

- conditions;
- primary task types;
- primary outcomes;
- replication criteria;
- stopping rules;

requires a new versioned preregistration rather than silent modification of this
one.

---

## 16. Current claim status

At the time of this preregistration:

- no benchmark dataset has been frozen;
- no confirmatory model outputs have been collected;
- no claim of sociolinguistic bias or invariance is being made;
- no mechanistic interpretation is warranted.