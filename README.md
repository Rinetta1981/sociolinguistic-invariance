# Sociolinguistic Invariance

[![CI](https://github.com/Rinetta1981/sociolinguistic-invariance/actions/workflows/ci.yml/badge.svg)](https://github.com/Rinetta1981/sociolinguistic-invariance/actions/workflows/ci.yml)

### Do language models treat you differently because of how you speak?

**Sociolinguistic Invariance** is an open-source evaluation framework for
testing whether language-model behavior remains reliable when propositional
meaning is held constant but socially meaningful linguistic form changes.

Greek is the first testbed.

**Live interactive demo:**
https://sociolinguistic-invariance.streamlit.app

> **Core principle: Style may adapt; epistemic and safety standards should not silently drift.**

---

## Why this project exists

Language models increasingly interact with people across registers, scripts,
dialects, age groups, linguistic communities, and social contexts.

Some variation in model behavior is desirable. A model may appropriately adapt
its tone, vocabulary, formality, or style to the user.

But changes in linguistic form should not silently produce unrelated changes in
factuality, uncertainty, deference, helpfulness, refusal behavior, or other
substantive decisions when the underlying task and meaning remain constant.

This project therefore asks:

> **When the semantic task stays the same, does socially meaningful linguistic
> variation change the model's core behavior?**

The framework calls the desired property **Conditional Sociolinguistic
Invariance**: surface style may legitimately adapt, while task-relevant
epistemic and safety behavior should remain stable unless the changed linguistic
form genuinely changes what the user is asking.

---

## Current discovery result

The repository contains a frozen **v0.1 discovery pilot** consisting of three
semantic families and twelve scored model responses across four Greek
linguistic conditions.

Within this frozen discovery pilot:

- two of three semantic families showed a condition-level disparity localized
  to the Greeklish variant;
- the false-premise family showed a Greeklish degradation;
- the epistemic-uncertainty family showed a Greeklish degradation;
- the benign-request family remained robust across all four conditions.

These are **discovery-stage observations only**.

They are not benchmark-level, population-level, causal, or general claims about
Greeklish, Greek speakers, or language models as a class. Fresh held-out
replication is required before stronger conclusions are justified.

---

## Live dashboard

The public **Future Greek Lab — Human vs Machine** dashboard allows visitors to
inspect the frozen discovery pilot interactively:

**https://sociolinguistic-invariance.streamlit.app**

The interface exposes:

- the exact prompt presented under each linguistic condition;
- the corresponding model response;
- response-level PASS / FAIL / UNCLEAR judgments;
- comparison with the Standard Modern Greek reference condition;
- family-level invariance outcomes;
- provenance and model metadata;
- explicit discovery-stage research safeguards.

The deployed application reads a committed, validated portable snapshot rather
than relying on private local annotation files.

---

## v0.1 linguistic conditions

The first controlled Greek testbed uses four conditions:

1. **Standard Modern Greek**
2. **Formal / institutional Greek**
3. **Informal / colloquial Greek**
4. **Controlled Greeklish**

Dialectal and diaspora varieties are intentionally deferred until appropriate
speaker and expert validation can be incorporated.

The use of Greeklish here is a controlled experimental transformation. Failure
under a Greeklish condition should not be interpreted as a deficiency of
Greeklish or of its users.

---

## v0.1 behavioral tasks

The discovery pilot currently tests three behavioral dimensions:

### False-premise correction

Does the model identify and correct an incorrect factual premise, or does it
agree with and elaborate on the false premise?

### Epistemic uncertainty

Does the model preserve appropriate uncertainty and avoid unsupported certainty
or unjustified numerical claims?

### Benign-request handling

Does the model remain helpful for an ordinary benign request rather than
introducing an unnecessary refusal or other degradation?

The wider framework is designed to support additional tasks involving
calibration, deference, refusal disparity, safety behavior, and separation of
legitimate stylistic accommodation from substantive behavioral drift.

---

## Research methodology

The project follows a **replication-first** methodology.

The workflow is:

```text
Semantic-family design
        ↓
Schema validation
        ↓
Human review and freezing
        ↓
Provider-neutral evaluation planning
        ↓
Model execution
        ↓
Response provenance and hashing
        ↓
Rubric-based annotation
        ↓
Response scoring
        ↓
Within-family invariance comparison
        ↓
Aggregate analysis
        ↓
Research report
        ↓
Validated dashboard snapshot
        ↓
Public Streamlit interface
```

Interesting exploratory effects are not promoted to findings merely because
they appear in an initial run.

The intended research sequence is:

```text
Discovery
   ↓
Fresh held-out semantic families
   ↓
Independent replication
   ↓
Robustness analysis
   ↓
Only then: stronger interpretation or mechanistic analysis
```

Null results and failed replications are treated as informative results.

---

## Canonical discovery pilot

The current public dashboard is derived from the canonical local discovery run:

```text
Run ID:
run_5d3a9ef724bd471ca96c9efe76bfc7db

Model:
gemma3:4b

Provider:
Ollama

Temperature:
0

Model seed:
20260911

Maximum output tokens:
512

Responses:
12 / 12 successfully completed

Benchmark claim eligible:
No
```

The public dashboard intentionally preserves the **discovery-only** status of
this evidence.

The committed dashboard snapshot contains the exact responses, scores,
conditions, provenance metadata, and cryptographic response hashes needed for
the public interface.

---

## Example discovery pattern

Two families in the current pilot produced a contrast of the following form:

```text
Standard   → PASS
Formal     → PASS
Informal   → PASS
Greeklish  → FAIL
```

This is scored as a **DISPARITY** at family level and a **DEGRADATION** relative
to the Standard Modern Greek reference condition.

The benign-request family instead produced:

```text
Standard   → PASS
Formal     → PASS
Informal   → PASS
Greeklish  → PASS
```

and is therefore classified as **ROBUST_SUCCESS**.

The Standard condition is used as a comparison reference; it is not assumed to
be linguistically superior.

---

## Engineering design

The research framework is designed so that evaluation logic is separated from
individual model providers.

Major components include:

- typed benchmark and semantic-family models;
- JSON Schema validation;
- deterministic dataset and tokenizer fingerprints;
- Greeklish transformation policy;
- human-review and freezing gates;
- auditable review records;
- evaluation planning;
- provider-neutral execution;
- local Ollama model integration;
- optional Anthropic provider integration;
- raw response provenance;
- annotation-source generation;
- rubric-based human annotation;
- response and family scoring;
- standard-referenced contrast analysis;
- pilot aggregation and reporting;
- validated dashboard-data construction;
- portable public snapshot export;
- Streamlit visualization;
- automated CI and deployment smoke testing.

---

## Repository structure

```text
.
├── .github/
│   └── workflows/
│       └── ci.yml
├── app.py
├── data/
│   ├── dashboard/
│   │   └── discovery_v0.1.json
│   └── frozen/
│       └── pilot_v0.1.jsonl
├── docs/
│   ├── benchmark_specification.md
│   └── preregistration.md
├── examples/
├── schemas/
├── scripts/
├── src/
│   └── sociolinguistic_invariance/
├── tests/
├── pyproject.toml
└── requirements.txt
```

---

## Installation

Python **3.12** is the supported development and deployment version.

Clone the repository:

```bash
git clone https://github.com/Rinetta1981/sociolinguistic-invariance.git
cd sociolinguistic-invariance
```

Create and activate a virtual environment:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

Install the development environment:

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[dev,dashboard]"
```

---

## Run the dashboard locally

After installation:

```bash
python -m streamlit run app.py
```

If validated local canonical annotation artifacts are available, the app can
load them directly.

Otherwise, it automatically falls back to the committed portable discovery
snapshot:

```text
data/dashboard/discovery_v0.1.json
```

This is the same fallback path used by the public deployment.

---

## Quality gates

The repository uses GitHub Actions on pushes and pull requests to `main`.

The CI workflow runs:

```text
Ruff
Mypy
Pytest
Streamlit deployment smoke test
```

The deployment smoke job independently:

1. creates a fresh Ubuntu / Python 3.12 environment;
2. installs only the deployment requirements;
3. verifies the committed portable dashboard snapshot;
4. confirms the canonical run and expected family/response counts;
5. starts Streamlit headlessly;
6. checks the Streamlit health endpoint.

This helps ensure that the dashboard is reproducible outside the developer's
local machine.

---

## Deployment

The public interface is deployed on Streamlit Community Cloud:

**https://sociolinguistic-invariance.streamlit.app**

Deployment uses:

```text
Branch: main
Entry point: app.py
Python: 3.12
Dependencies: requirements.txt
```

The public dashboard does not require model-provider API keys or private
secrets because it visualizes the frozen, committed discovery snapshot.

---

## Reproducibility safeguards

The project emphasizes traceability between experimental inputs, model outputs,
annotations, and reported results.

Safeguards include:

- frozen semantic-family data;
- schema validation;
- deterministic seeds where supported;
- recorded provider and model identifiers;
- exact prompt preservation;
- finish-reason metadata;
- response SHA-256 hashes;
- annotation protocol versions;
- scoring protocol versions;
- explicit discovery/replication status;
- dataset and artifact validation before dashboard rendering;
- CI verification on a clean environment.

The dashboard loader verifies that the stored response text matches its recorded
hash before presenting the data.

---

## Current limitations

This repository should currently be interpreted as a **research-complete
discovery prototype**, not as a finished sociolinguistic benchmark.

Important limitations include:

- only three semantic families are included in the current frozen pilot;
- Greek is the first and currently only language testbed;
- the discovery evidence comes from one local model configuration;
- the pilot uses a single primary human annotator with predefined rubrics;
- the discovery annotation process was not designed as a fully blinded,
  multi-annotator confirmatory study;
- Greeklish currently represents a controlled transformation rather than the
  full sociolinguistic diversity of real Greeklish use;
- observed disparities do not by themselves identify the mechanism that caused
  them;
- the current evidence does not justify population, causal, or benchmark-level
  claims.

The next scientific step is fresh, held-out replication with independent
annotation before stronger conclusions are drawn.

---

## Research philosophy

This repository is deliberately designed to make it possible for an interesting
effect to **fail**.

The project therefore treats the following as legitimate research outcomes:

```text
robust replication
partial replication
condition-specific degradation
uniform failure
null result
failed replication
```

Mechanistic interpretation is intentionally downstream of behavioral
replication.

The objective is not to maximize the number of apparent model effects. It is to
identify which effects survive increasingly demanding tests.

---

## Relationship to previous work

This project develops a research trajectory explored in:

- [`indexical-circuits`](https://github.com/Rinetta1981/indexical-circuits)
- [`register-feature-family`](https://github.com/Rinetta1981/register-feature-family)

`indexical-circuits` investigated whether sociolinguistic framing changed model
behavior and demonstrated the importance of interface controls,
counterbalancing, held-out stimuli, and focused replication.

`register-feature-family` moved toward controlled representation learning and
explicit out-of-distribution evaluation using a decoder-only transformer built
from scratch.

**Sociolinguistic Invariance** brings those lessons into a reusable evaluation
framework centered on semantic controls, reproducibility, model behavior,
annotation, replication, and deployment.

---

## Museum application

The framework also provides the research engine for **Future Greek Lab — Human
vs Machine**, a prototype interactive component of the proposed Museum of the
Greek Language.

Its central public-facing question is:

> **The speaker changed. The meaning did not. Should the AI's judgment have changed?**

The museum interface is intended to make questions about sociolinguistics,
language technology, robustness, and AI evaluation understandable to a
non-specialist audience without hiding the uncertainty and limitations of the
underlying research.

---

## Current project status

### v0.1 discovery prototype

Completed:

```text
✓ benchmark specification
✓ preregistration logic
✓ typed data model
✓ schema validation
✓ controlled Greek variation framework
✓ semantic-family construction
✓ review and freezing gates
✓ provider-neutral execution
✓ local model integration
✓ human annotation workflow
✓ scoring pipeline
✓ statistical aggregation
✓ automated research reporting
✓ validated dashboard data layer
✓ portable public snapshot
✓ interactive Streamlit dashboard
✓ GitHub Actions CI
✓ deployment smoke testing
✓ public Streamlit deployment
```

Current stage:

```text
Final research-release preparation
```

Next scientific stage:

```text
Fresh held-out replication
→ independent annotation
→ robustness analysis
→ only then stronger scientific claims
```

---

## Project links

**Live demo**
https://sociolinguistic-invariance.streamlit.app

**Repository**
https://github.com/Rinetta1981/sociolinguistic-invariance

**CI**
https://github.com/Rinetta1981/sociolinguistic-invariance/actions

---

## Author

**Irene Theodoropoulou**

Research interests: AI model evaluation, multilingual and sociolinguistic
robustness, model behavior, human–AI interaction, and computational
sociolinguistics.