import json
from collections.abc import Sequence
from pathlib import Path
from typing import Final

from sociolinguistic_invariance.evaluation import (
    EvaluationResult,
    ModelConfiguration,
    ResponseStatus,
    evaluation_result_to_dict,
)
from sociolinguistic_invariance.evaluation_plan import (
    EvaluationPlan,
    evaluation_plan_to_dict,
)
from sociolinguistic_invariance.execution import (
    EvaluationExecutor,
)
from sociolinguistic_invariance.provenance import (
    GitProvenance,
    git_provenance_to_dict,
)

RAW_RESULTS_FORMAT_VERSION: Final = (
    "raw-results-v0.1"
)


def execute_evaluation_plan(
    *,
    plan: EvaluationPlan,
    executor: EvaluationExecutor,
) -> tuple[EvaluationResult, ...]:
    """Execute every request in one evaluation plan."""

    results: list[EvaluationResult] = []

    for request in plan.requests:
        if request.run_id != plan.run_id:
            raise ValueError(
                "Evaluation request run_id does not "
                "match evaluation plan run_id."
            )

        result = executor.execute_request(
            request
        )

        if result.run_id != plan.run_id:
            raise RuntimeError(
                "Evaluation result run_id does not "
                "match evaluation plan run_id."
            )

        if result.request_id != request.request_id:
            raise RuntimeError(
                "Evaluation result request_id does not "
                "match its evaluation request."
            )

        results.append(
            result
        )

    return tuple(
        results
    )


def count_result_statuses(
    results: Sequence[EvaluationResult],
) -> dict[str, int]:
    """Count final result statuses deterministically."""

    counts = {
        status.value: 0
        for status in ResponseStatus
    }

    for result in results:
        counts[
            result.status.value
        ] += 1

    return counts


def _model_configuration_to_dict(
    configuration: ModelConfiguration,
) -> dict[str, object]:
    """Serialize model configuration for raw artifacts."""

    return {
        "provider": configuration.provider,
        "requested_model": (
            configuration.requested_model
        ),
        "temperature": configuration.temperature,
        "top_p": configuration.top_p,
        "max_output_tokens": (
            configuration.max_output_tokens
        ),
        "seed": configuration.seed,
        "system_instruction": (
            configuration.system_instruction
        ),
        "sdk_version": configuration.sdk_version,
    }


def _validate_result_alignment(
    *,
    plan: EvaluationPlan,
    configuration: ModelConfiguration,
    results: Sequence[EvaluationResult],
) -> None:
    """Ensure raw results align exactly with their plan."""

    if len(results) != plan.request_count:
        raise ValueError(
            "Evaluation result count does not "
            "match evaluation plan request count."
        )

    for request, result in zip(
        plan.requests,
        results,
        strict=True,
    ):
        if result.run_id != plan.run_id:
            raise ValueError(
                "Evaluation result run_id does not "
                "match evaluation plan."
            )

        if result.request_id != request.request_id:
            raise ValueError(
                "Evaluation result order does not "
                "match evaluation plan."
            )

        if result.prompt_sha256 != request.prompt_sha256:
            raise ValueError(
                "Evaluation result prompt SHA-256 does "
                "not match evaluation request."
            )

        if result.provider != configuration.provider:
            raise ValueError(
                "Evaluation result provider does not "
                "match model configuration."
            )

        if (
            result.requested_model
            != configuration.requested_model
        ):
            raise ValueError(
                "Evaluation result requested model does "
                "not match model configuration."
            )


def build_raw_results_payload(
    *,
    plan: EvaluationPlan,
    configuration: ModelConfiguration,
    provenance: GitProvenance,
    results: Sequence[EvaluationResult],
) -> dict[str, object]:
    """Build one self-contained unscored result artifact."""

    _validate_result_alignment(
        plan=plan,
        configuration=configuration,
        results=results,
    )

    return {
        "artifact_type": "raw_evaluation_results",
        "raw_results_format_version": (
            RAW_RESULTS_FORMAT_VERSION
        ),
        "run_id": plan.run_id,
        "artifact_id": plan.artifact_id,
        "artifact_sha256": plan.artifact_sha256,
        "git_provenance": git_provenance_to_dict(
            provenance
        ),
        "model_configuration": (
            _model_configuration_to_dict(
                configuration
            )
        ),
        "plan": evaluation_plan_to_dict(
            plan
        ),
        "result_count": len(
            results
        ),
        "status_counts": count_result_statuses(
            results
        ),
        "results": [
            evaluation_result_to_dict(
                result
            )
            for result in results
        ],
    }


def default_raw_results_path(
    run_id: str,
) -> Path:
    """Return the conventional path for one raw run."""

    if not run_id.strip():
        raise ValueError(
            "run_id must be non-blank."
        )

    return (
        Path("results")
        / "raw"
        / f"{run_id}.json"
    )


def write_raw_results_atomic(
    *,
    path: Path,
    payload: dict[str, object],
    overwrite: bool = False,
) -> None:
    """Persist raw results atomically."""

    if path.exists() and not overwrite:
        raise FileExistsError(
            f"Raw result file already exists: {path}. "
            "Use overwrite=True only when replacement "
            "is intentional."
        )

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path = path.with_suffix(
        path.suffix + ".tmp"
    )

    temporary_path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    temporary_path.replace(
        path
    )