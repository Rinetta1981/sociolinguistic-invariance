# Raw Evaluation Results Format

## Version

`raw-results-v0.1`

## Purpose

A raw evaluation-results artifact records the provider-neutral outputs of
one complete evaluation run before benchmark scoring or scientific
interpretation.

Raw results are intentionally separated from annotations and derived
scores.

The separation preserves the original execution record so that scoring
rules can be inspected, revised, or independently reproduced without
altering the provider outputs.

## Artifact identity

Each artifact has:

- `artifact_type`: `raw_evaluation_results`;
- `raw_results_format_version`: the serialization format version;
- `run_id`: the unique evaluation-run identifier;
- `artifact_id`: the frozen benchmark artifact identifier;
- `artifact_sha256`: the SHA-256 digest of the frozen benchmark.

The benchmark digest binds the raw responses to the exact frozen input
artifact used during execution.

## Git provenance

The artifact contains a `git_provenance` object recording:

- whether Git provenance was available;
- the current Git commit;
- whether the working tree was clean;
- the number of Git status entries;
- a SHA-256 digest of the Git porcelain-status text.

Generated mock artifacts MAY be produced from a dirty development tree.

Real benchmark executions intended to support reported findings MUST
satisfy the clean-provenance requirements specified in
`docs/evaluation_protocol.md` before external provider requests are made.

## Model configuration

The `model_configuration` object records the requested execution
configuration, including:

- provider;
- requested model;
- temperature;
- top-p;
- maximum output tokens;
- model-generation seed, where used;
- system instruction;
- SDK version, where recorded.

These fields describe the requested configuration rather than making a
claim that every provider implements each parameter identically.

## Evaluation plan

The complete `plan` is embedded in the raw artifact.

This records:

- prompt order;
- request identifiers;
- semantic-family identifiers;
- task types;
- sociolinguistic conditions;
- exact prompt text;
- prompt SHA-256 digests;
- ordering seed and randomization state.

Embedding the plan permits each raw result to be traced back to its exact
evaluation request.

## Results

`results` is an ordered list containing one provider-neutral
`EvaluationResult` for each planned request.

Each result records execution metadata including:

- run identifier;
- request identifier;
- semantic-family identifier;
- task type;
- sociolinguistic condition;
- provider;
- requested model;
- prompt SHA-256;
- final execution status;
- request and response timestamps;
- total measured latency;
- complete attempt history;
- response text when successful;
- provider request identifier when available;
- token usage when available;
- error type and message when execution fails.

Raw results do not contain benchmark PASS, FAIL, or UNCLEAR judgments.
Those belong to the separate annotation and scoring layers.

## Attempt history

Every actual provider attempt is preserved.

An attempt contains:

- attempt number;
- execution status;
- start and finish timestamps;
- measured latency;
- provider request identifier when available;
- error type and message when relevant.

Transient failures that are retried therefore remain visible rather than
being erased by a later successful attempt.

## Status counts

The top-level `status_counts` object summarizes final request statuses for
the run.

The defined statuses are:

- `SUCCESS`;
- `PROVIDER_ERROR`;
- `TIMEOUT`;
- `RATE_LIMITED`;
- `INVALID_RESPONSE`;
- `SKIPPED`.

Counts are descriptive execution metadata. They are not benchmark scores.

## Ordering and alignment

The number of serialized results MUST equal the evaluation plan request
count.

For each position in the run:

- the result `run_id` must match the plan;
- the result `request_id` must match the corresponding request;
- the result prompt SHA-256 must match the corresponding request;
- the result provider must match the model configuration;
- the requested model must match the model configuration.

A raw artifact that violates these alignment requirements must not be
written as a valid evaluation record.

## Mock execution

The scripted mock provider is an engineering test mechanism.

Mock outputs are explicitly marked with text beginning:

```text
[MOCK] No model inference performed