import argparse
from pathlib import Path
from typing import Final

from sociolinguistic_invariance.batch_execution import (
    write_raw_results_atomic,
)
from sociolinguistic_invariance.evaluation import (
    EvaluationRequest,
    ModelConfiguration,
    ResponseStatus,
    evaluation_result_to_dict,
    new_run_id,
)
from sociolinguistic_invariance.evaluation_plan import (
    build_evaluation_plan,
)
from sociolinguistic_invariance.execution import (
    EvaluationExecutor,
    RetryPolicy,
)
from sociolinguistic_invariance.ollama_provider import (
    OllamaProvider,
)
from sociolinguistic_invariance.provenance import (
    GitProvenance,
    capture_git_provenance,
    git_provenance_to_dict,
    require_clean_git_worktree,
)

LOCAL_SMOKE_FORMAT_VERSION: Final = (
    "ollama-local-smoke-v0.1"
)

REPO_ROOT: Final = (
    Path(__file__).resolve().parents[1]
)

ARTIFACT_PATH: Final = (
    REPO_ROOT
    / "data"
    / "frozen"
    / "pilot_v0.1.jsonl"
)

MANIFEST_PATH: Final = (
    REPO_ROOT
    / "data"
    / "frozen"
    / "pilot_v0.1.manifest.json"
)

MAX_OUTPUT_TOKENS: Final = 128

LOCAL_SEED: Final = 20260911

SYSTEM_INSTRUCTION: Final = (
    "Answer the user's request directly and accurately."
)


def _build_parser() -> argparse.ArgumentParser:
    """Construct the guarded local-smoke CLI."""

    parser = argparse.ArgumentParser(
        description=(
            "Execute exactly one frozen benchmark "
            "request against a local Ollama model. "
            "No paid external API is used."
        )
    )

    parser.add_argument(
        "--model",
        required=True,
        help=(
            "Exact locally installed Ollama "
            "model identifier."
        ),
    )

    parser.add_argument(
        "--execute-local",
        action="store_true",
        help=(
            "Explicitly authorize one local "
            "model inference."
        ),
    )

    return parser


def _require_local_confirmation(
    *,
    confirmed: bool,
    parser: argparse.ArgumentParser,
) -> None:
    """Require explicit authorization for inference."""

    if not confirmed:
        parser.error(
            "Local execution is disabled by default. "
            "Pass --execute-local to authorize exactly "
            "one local model inference."
        )


def _require_clean_provenance(
    *,
    provenance: GitProvenance,
    parser: argparse.ArgumentParser,
) -> None:
    """Require auditable committed source state."""

    if not provenance.available:
        parser.error(
            "Local evaluation requires available "
            "Git provenance."
        )

    if provenance.worktree_clean is not True:
        parser.error(
            "Local evaluation requires a clean "
            "Git working tree."
        )

    require_clean_git_worktree(
        provenance
    )


def _request_to_dict(
    request: EvaluationRequest,
) -> dict[str, object]:
    """Serialize the selected evaluation request."""

    return {
        "run_id": request.run_id,
        "request_id": request.request_id,
        "family_id": request.family_id,
        "task_type": request.task_type.value,
        "condition": request.condition.value,
        "prompt_text": request.prompt_text,
        "prompt_sha256": request.prompt_sha256,
        "order_index": request.order_index,
    }


def _configuration_to_dict(
    configuration: ModelConfiguration,
) -> dict[str, object]:
    """Serialize local model configuration."""

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


def _smoke_output_path(
    *,
    run_id: str,
) -> Path:
    """Return the conventional smoke output path."""

    return (
        REPO_ROOT
        / "results"
        / "smoke"
        / f"{run_id}.json"
    )


def main() -> int:
    """Execute one guarded local Ollama request."""

    parser = _build_parser()
    args = parser.parse_args()

    _require_local_confirmation(
        confirmed=args.execute_local,
        parser=parser,
    )

    model = str(
        args.model
    ).strip()

    if not model:
        parser.error(
            "--model must be non-blank."
        )

    provenance = capture_git_provenance(
        REPO_ROOT
    )

    _require_clean_provenance(
        provenance=provenance,
        parser=parser,
    )

    run_id = new_run_id()

    plan = build_evaluation_plan(
        run_id=run_id,
        artifact_path=ARTIFACT_PATH,
        manifest_path=MANIFEST_PATH,
        randomized=False,
        order_seed=None,
    )

    if plan.request_count < 1:
        raise RuntimeError(
            "Frozen evaluation plan contained "
            "no requests."
        )

    request = plan.requests[
        0
    ]

    configuration = ModelConfiguration(
        provider="ollama",
        requested_model=model,
        temperature=0.0,
        top_p=None,
        max_output_tokens=MAX_OUTPUT_TOKENS,
        seed=LOCAL_SEED,
        system_instruction=SYSTEM_INSTRUCTION,
        sdk_version=None,
    )

    provider = OllamaProvider()

    executor = EvaluationExecutor(
        provider=provider,
        configuration=configuration,
        retry_policy=RetryPolicy(
            max_attempts=1,
            initial_backoff_seconds=0.0,
            max_backoff_seconds=0.0,
        ),
    )

    result = executor.execute_request(
        request
    )

    payload: dict[str, object] = {
        "artifact_type": (
            "ollama_local_smoke"
        ),
        "local_smoke_format_version": (
            LOCAL_SMOKE_FORMAT_VERSION
        ),
        "run_id": run_id,
        "artifact_id": plan.artifact_id,
        "artifact_sha256": (
            plan.artifact_sha256
        ),
        "git_provenance": (
            git_provenance_to_dict(
                provenance
            )
        ),
        "model_configuration": (
            _configuration_to_dict(
                configuration
            )
        ),
        "planned_request_count": (
            plan.request_count
        ),
        "executed_request_count": 1,
        "provider_attempt_limit": 1,
        "paid_api_used": False,
        "benchmark_claim_eligible": False,
        "request": _request_to_dict(
            request
        ),
        "result": (
            evaluation_result_to_dict(
                result
            )
        ),
    }

    output_path = _smoke_output_path(
        run_id=run_id
    )

    write_raw_results_atomic(
        path=output_path,
        payload=payload,
    )

    relative_output_path = (
        output_path.relative_to(
            REPO_ROOT
        )
    )

    print(
        "Ollama local smoke execution complete."
    )
    print(
        f"Run ID: {run_id}"
    )
    print(
        f"Model requested: {model}"
    )
    print(
        f"Family: {request.family_id}"
    )
    print(
        "Condition: "
        f"{request.condition.value}"
    )
    print(
        f"Status: {result.status.value}"
    )
    print(
        "Provider attempts: "
        f"{len(result.attempts)}"
    )
    print(
        "Returned model: "
        f"{result.returned_model}"
    )
    print(
        "Finish reason: "
        f"{result.finish_reason}"
    )

    if result.usage is not None:
        print(
            "Input tokens: "
            f"{result.usage.input_tokens}"
        )
        print(
            "Output tokens: "
            f"{result.usage.output_tokens}"
        )
        print(
            "Total tokens: "
            f"{result.usage.total_tokens}"
        )

    print(
        "Latency seconds: "
        f"{result.latency_seconds:.6f}"
    )
    print(
        "Git worktree clean: "
        f"{provenance.worktree_clean}"
    )
    print(
        f"Output: {relative_output_path}"
    )
    print(
        "Maximum local provider attempts: 1"
    )
    print(
        "Paid API used: False"
    )
    print(
        "Benchmark claim eligible: False"
    )

    if (
        result.status
        is ResponseStatus.SUCCESS
    ):
        print(
            "Response:"
        )
        print(
            result.response_text
        )

        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(
        main()
    )