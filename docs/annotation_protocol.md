# Response Annotation Protocol

## Version

`annotation-protocol-v0.1`

## Purpose

This protocol defines the annotation layer between raw model responses
and benchmark scoring.

The central principle is that annotation and scoring are separate
operations.

Annotation records what an evaluator observes in a response.

Scoring later applies preregistered rules to those annotations.

The separation prevents a scorer from silently changing an observation
in order to produce a preferred benchmark outcome.

## Pipeline position

The intended evaluation sequence is:

```text
Frozen benchmark
      |
      v
Model execution
      |
      v
Raw response
      |
      v
Criterion annotation
      |
      v
PASS / FAIL / UNCLEAR scoring
      |
      v
Family-level invariance analysis