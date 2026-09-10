# Sociolinguistic Invariance Evaluation Protocol

Version: 0.1

Status: Pre-evaluation specification

## 1. Purpose

This document defines how frozen Sociolinguistic Invariance benchmark
items are submitted to language models and how model outputs are
recorded.

The evaluation protocol is specified before substantive model outputs
are collected.

Its purpose is to make model evaluation:

- reproducible;
- auditable;
- provider-independent where possible;
- resistant to accidental prompt changes;
- explicit about model configuration;
- explicit about failures and retries;
- suitable for later statistical analysis.

The initial `pilot_v0.1` artifact contains only three semantic families
and is intended for engineering validation rather than confirmatory
scientific inference.

---

## 2. Evaluation unit

The basic evaluation unit is one model response to one prompt variant.

Each evaluation unit therefore corresponds to:

- one semantic family;
- one variation condition;
- one task type;
- one exact prompt text;
- one model;
- one model configuration;
- one run identifier.

For the current pilot there are:

- 3 semantic families;
- 4 conditions per family;
- 12 prompt variants per model run.

---

## 3. Frozen input requirement

Evaluation must use frozen benchmark artifacts.

For the initial pilot, the canonical input artifact is:

`data/frozen/pilot_v0.1.jsonl`

The corresponding manifest is:

`data/frozen/pilot_v0.1.manifest.json`

Before evaluation, the runner must verify the SHA-256 checksum of the
frozen export against the checksum recorded in the manifest.

If the hashes do not match, evaluation must stop.

The runner must not silently use mutable draft data in
`data/discovery/` as a substitute for the frozen artifact.

---

## 4. Prompt preservation

The exact frozen prompt text must be sent to the model without
sociolinguistic rewriting by the evaluation runner.

The runner must not:

- correct spelling;
- standardize Greeklish;
- normalize register;
- paraphrase prompts;
- add demographic descriptions;
- infer speaker characteristics;
- modify punctuation for stylistic reasons.

Provider-required message formatting may be applied, but the benchmark
prompt itself must remain unchanged.

---

## 5. System instruction

The evaluation runner should use a minimal, prespecified system
instruction where the provider requires or supports one.

For pilot version 0.1, the default system instruction is:

`Answer the user's request directly and accurately.`

The same system instruction must be used for all sociolinguistic
conditions within a run.

A provider that does not support system instructions may omit it, but
that difference must be recorded in run metadata.

---

## 6. Model configuration

Every evaluation run must record at least:

- provider;
- requested model identifier;
- returned model identifier where available;
- temperature where configurable;
- top-p where configurable;
- maximum output tokens where configurable;
- seed where supported;
- system instruction;
- API or SDK version where available;
- run timestamp.

Unsupported configuration fields must be recorded as unavailable rather
than silently invented.

---

## 7. Decoding defaults

For pilot engineering evaluation, deterministic or minimally stochastic
decoding is preferred.

The initial default configuration is:

- temperature: 0 where supported;
- top-p: provider default unless explicitly fixed;
- seed: fixed where supported;
- maximum output tokens: sufficient to complete the task without
  encouraging unnecessary verbosity.

Provider-specific limitations must be recorded.

The benchmark must not claim exact reproducibility when the provider
does not guarantee deterministic outputs.

---

## 8. Run identifier

Every model evaluation must receive a unique run identifier.

A run identifier should identify one execution of one frozen artifact
against one model configuration.

The run identifier must be recorded with every response.

The exact run identifier format is an implementation detail, but it must
be stable, machine-readable, and collision-resistant for normal project
use.

---

## 9. Request identifier

Every prompt submission must receive a unique request identifier.

The request identifier must make it possible to distinguish repeated
calls to the same family and condition.

A request record must preserve:

- run identifier;
- request identifier;
- family identifier;
- task type;
- variation condition;
- prompt text;
- prompt SHA-256.

The prompt SHA-256 makes accidental prompt mutation detectable after
evaluation.

---

## 10. Response record

Every completed model request must preserve at least:

- run identifier;
- request identifier;
- family identifier;
- task type;
- variation condition;
- provider;
- requested model identifier;
- returned model identifier where available;
- response text;
- response status;
- request timestamp;
- response timestamp;
- latency;
- retry count;
- prompt SHA-256;
- evaluation protocol version.

Where the provider supplies them, the following should also be stored:

- input token count;
- output token count;
- total token count;
- provider request identifier;
- finish reason;
- usage metadata.

---

## 11. Response status

Each model call receives one machine-readable execution status.

Initial statuses are:

### SUCCESS

The provider returned a usable model response.

### PROVIDER_ERROR

The provider returned an API or service error.

### TIMEOUT

The request exceeded the configured timeout.

### RATE_LIMITED

The provider rejected or delayed the request because of rate limits.

### INVALID_RESPONSE

A response was returned but could not be interpreted as the expected
textual model output.

### SKIPPED

The request was intentionally not executed.

Execution status is distinct from benchmark scoring.

For example, a technically successful API response can later receive a
benchmark score of FAIL.

---

## 12. Retries

Retries must be bounded and recorded.

The runner must never retry indefinitely.

For transient failures such as rate limits, timeouts, or temporary
provider errors, the runner may retry according to a prespecified
policy.

Every retry must preserve:

- the original request identifier or a traceable parent identifier;
- attempt number;
- failure reason;
- elapsed time.

A successful retry must not erase evidence that earlier attempts failed.

---

## 13. Ordering

Prompt order should not systematically confound sociolinguistic
condition.

The evaluation runner should therefore support deterministic randomized
ordering using a recorded seed.

Within-family condition order must not always be:

standard -> formal -> informal -> greeklish

when evaluating models for substantive experiments.

For pipeline-development tests, fixed order is permitted if clearly
marked as engineering-only.

---

## 14. Blinding and scoring separation

The evaluation runner collects model responses.

It does not decide whether those responses PASS or FAIL.

Scoring occurs in a separate stage under:

`scoring-protocol-v0.1`

This separation prevents model execution code from silently embedding
post-hoc scoring decisions.

Raw model responses must be preserved before annotation.

---

## 15. Raw and derived data separation

Raw provider responses and derived annotations must be stored
separately.

A recommended structure is:

`results/raw/`

for model outputs and execution metadata, and:

`results/annotations/`

for human or validated automated annotations.

Subsequent family-level summaries should be stored separately from both.

Raw results must not be overwritten by scoring.

---

## 16. Error preservation

Failures are data.

A provider error, timeout, invalid response, or rate-limit event must not
simply disappear from the dataset.

The runner must preserve enough information to reconstruct:

- what was attempted;
- when it was attempted;
- what failed;
- whether it was retried;
- whether a later attempt succeeded.

Secrets, credentials, authorization headers, and sensitive provider
information must never be written to result files.

---

## 17. Credentials

API credentials must never be committed to Git.

Secrets should be supplied through environment variables or another
secure runtime mechanism.

The repository must not contain:

- API keys;
- bearer tokens;
- passwords;
- private account identifiers;
- copied authorization headers.

Example environment-variable names may appear in documentation, but
their values must not.

---

## 18. Latency

For every executed request, the runner should record elapsed wall-clock
latency.

Latency should be measured with a monotonic clock.

The project may later report summaries such as:

- median latency;
- p95 latency;
- latency by provider;
- latency by model;
- latency by condition.

Latency differences are operational metrics and must not be interpreted
as sociolinguistic effects without an appropriate design.

---

## 19. Cost

Where reliable provider pricing and usage metadata are available, the
evaluation pipeline may calculate approximate request cost.

Cost calculations must record:

- pricing source or pricing version;
- token counts used;
- calculation timestamp or pricing snapshot;
- currency.

Estimated cost must be clearly distinguished from provider-billed cost.

The initial runner may record usage first and add cost computation as a
separate layer.

---

## 20. Provider adapters

Provider-specific API code should be separated from benchmark logic.

The preferred architecture is:

benchmark runner
    |
    +-- provider-neutral request model
    |
    +-- OpenAI adapter
    |
    +-- Anthropic adapter
    |
    +-- additional adapters

The benchmark should not require core scoring or data structures to
change merely because another model provider is added.

---

## 21. Dry-run mode

The evaluation runner must support a dry-run or equivalent validation
mode before paid API requests are sent.

Dry-run mode should verify:

- frozen artifact integrity;
- prompt loading;
- request construction;
- run identifiers;
- request identifiers;
- ordering;
- output paths;
- configuration validation.

Dry-run mode must not contact an external model provider.

---

## 22. Pilot claim boundary

The initial `pilot_v0.1` evaluation exists to demonstrate and test the
end-to-end research-engineering pipeline.

It is not a sufficient sample for claims that a model is globally biased
toward or against:

- Standard Modern Greek;
- formal Greek;
- informal Greek;
- Greeklish;
- any Greek-speaking population.

Any observed difference at this stage is a pilot observation requiring
substantially broader discovery evaluation and independent replication.

---

## 23. Reproducibility record

A completed run should preserve enough metadata to reconstruct:

- which frozen artifact was used;
- the artifact SHA-256;
- which prompts were sent;
- their prompt SHA-256 hashes;
- which model was requested;
- what configuration was requested;
- the execution order;
- when requests were made;
- what responses were returned;
- what errors occurred;
- how many retries occurred.

The Git commit used for the evaluation should also be recorded where
possible.

---

## 24. Protocol version

This document defines:

`evaluation-protocol-v0.1`

Changes that alter request construction, retry behavior, ordering,
required metadata, or provider interaction semantics require a new
evaluation protocol version.

Typographical changes that do not alter execution semantics may be
documented without changing the substantive protocol version.

## Git provenance and execution state

Evaluation outputs MUST distinguish the identity of the most recent Git
commit from the state of the working tree at execution time.

Recording a Git commit identifier alone is insufficient to establish that
an evaluation was executed from exactly the committed source state. A
working tree may contain modified, staged, or untracked files that affect
execution while the repository still reports the identifier of an earlier
commit.

For this reason, evaluation infrastructure records structured Git
provenance with the following fields:

- `available`: whether Git provenance could be obtained;
- `commit`: the full Git object identifier for `HEAD`, when available;
- `worktree_clean`: whether the working tree contained no tracked or
  untracked changes at provenance capture time;
- `status_entry_count`: the number of entries reported by Git porcelain
  status;
- `status_sha256`: a SHA-256 digest of the exact porcelain-status text.

The status digest permits auditing of whether the recorded working-tree
state changed without embedding local filenames or filesystem paths in
evaluation artifacts.

### Dry-run behavior

Dry runs are engineering and validation operations. They MAY execute from
a dirty working tree.

When a dry run is executed from a dirty working tree, the artifact MUST
record that state explicitly. It MUST NOT represent the recorded `HEAD`
commit as sufficient evidence that the dry run corresponds exactly to the
committed source tree.

A dry-run artifact therefore records both the commit identifier and the
structured Git provenance object.

### Real evaluation behavior

A real external-model evaluation intended to contribute to reported
benchmark results MUST require reproducible Git provenance before any
provider request is sent.

Execution MUST stop before external model calls when either:

1. Git provenance is unavailable; or
2. the Git working tree is not clean.

A successful reproducible execution therefore requires:

```text
Git provenance available = true
Git working tree clean = true