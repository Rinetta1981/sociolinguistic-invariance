# Live Provider Execution Protocol

## Version

`live-execution-protocol-v0.1`

## Purpose

This protocol defines the safeguards required before the
`sociolinguistic-invariance` benchmark sends requests to an external
language-model provider.

Live execution is deliberately separated from benchmark construction,
evaluation planning, mock execution, annotation, scoring, and
statistical interpretation.

The initial supported external provider is Anthropic.

## Core principle

A live provider request is an external experimental action.

It may:

- transmit benchmark text to a third-party service;
- consume API credits;
- incur financial cost;
- return provider-specific metadata;
- fail because of network, authentication, rate-limit, model-access, or
  service errors.

For those reasons, live execution must never happen implicitly as a
side effect of importing the package, running ordinary tests, generating
an evaluation plan, or executing the scripted mock provider.

## No live calls during ordinary tests

The automated test suite MUST NOT require:

- an Anthropic API key;
- network connectivity;
- paid provider access;
- a particular Anthropic account;
- access to a particular production model.

Anthropic adapter tests use fake clients or local provider substitutes.

Tests exercising the live-runner logic must replace the real provider
before reaching any execution path capable of contacting Anthropic.

A passing test suite therefore does not itself make any external model
request.

## Explicit authorization

The Anthropic smoke-test runner is disabled by default.

Live execution requires the explicit command-line flag:

```text
--execute-live

## Normative initial smoke-test safeguards

The initial live-provider smoke test is deliberately narrower than a
scientific benchmark execution.

The provider-neutral retry policy is fixed to:

```text
max_attempts = 1

## Normative initial smoke-test safeguards

The initial live-provider smoke test is deliberately narrower than a
scientific benchmark execution.

The provider-neutral retry policy is fixed to:

```text
max_attempts = 1