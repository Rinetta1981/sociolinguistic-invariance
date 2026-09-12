import argparse
from pathlib import Path
from typing import Final

from sociolinguistic_invariance.batch_execution import (
    build_raw_results_payload,
    count_result_statuses,
    default_raw_results_path,
    execute_evaluation_plan,
    write_raw_results_atomic,
)
from sociolinguistic_invariance.evaluation import (
    ModelConfiguration,
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
    require_clean_git_worktree,
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

PILOT_FORMAT_VERSION: Final = (
    "ollama-local-pilot-v0.1"
)

ORDER_SEED: Final = 20260910

MODEL_SEED: Final = 20260911

MAX_OUTPUT_TOKENS: Final = 512

OLLAMA_TIMEOUT_SECONDS: Final = 120.0

EXPECTED_REQUEST_COUNT: Final = 12

SYSTEM_INSTRUCTION: Final = (
    "Answer the user's request directly and accurately."
)


def _build_parser() -> argparse.ArgumentParser:
    """Construct the guarded local-pilot CLI."""

    parser = argparse.ArgumentParser(
        description=(
            "Execute the complete frozen discovery "
            "pilot against a local Ollama model. "
            "Exactly 12 local model evaluations are "
            "expected. No paid external API is used."
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
            "Explicitly authorize the complete "
            "12-request local pilot."
        ),
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=(
            "Optional raw-results output path. "
            "Defaults to results/raw/<run_id>.json."
        ),
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
        help=(
            "Explicitly permit replacement if the "
            "chosen output path already exists."
        ),
    )

    return parser


def _require_local_confirmation(
    *,
    confirmed: bool,
    parser: argparse.ArgumentParser,
) -> None:
    """Require explicit authorization for local inference."""

    if not confirmed:
        parser.error(
            "Local execution is disabled by default. "
            "Pass --execute-local to authorize the "
            "complete 12-request local pilot."
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


def _require_expected_plan_size(
    *,
    request_count: int,
) -> None:
    """Require exactly the frozen 12-request pilot."""

    if request_count != EXPECTED_REQUEST_COUNT:
        raise RuntimeError(
            "Frozen pilot request count changed. "
            f"Expected {EXPECTED_REQUEST_COUNT}, "
            f"observed {request_count}."
        )


def main() -> int:
    """Execute the complete guarded local Ollama pilot."""

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
        randomized=True,
        order_seed=ORDER_SEED,
    )

    _require_expected_plan_size(
        request_count=plan.request_count
    )

    configuration = ModelConfiguration(
        provider="ollama",
        requested_model=model,
        temperature=0.0,
        top_p=None,
        max_output_tokens=MAX_OUTPUT_TOKENS,
        seed=MODEL_SEED,
        system_instruction=SYSTEM_INSTRUCTION,
        sdk_version=None,
    )

    provider = OllamaProvider(
        timeout_seconds=(
            OLLAMA_TIMEOUT_SECONDS
        )
    )

    executor = EvaluationExecutor(
        provider=provider,
        configuration=configuration,
        retry_policy=RetryPolicy(
            max_attempts=1,
            initial_backoff_seconds=0.0,
            max_backoff_seconds=0.0,
        ),
    )

    print(
        "Starting complete local Ollama pilot."
    )
    print(
        f"Run ID: {run_id}"
    )
    print(
        f"Model: {model}"
    )
    print(
        f"Requests: {plan.request_count}"
    )
    print(
        f"Order randomized: {plan.randomized}"
    )
    print(
        f"Order seed: {plan.order_seed}"
    )
    print(
        "Paid external API calls: 0"
    )
    print()

    results = execute_evaluation_plan(
        plan=plan,
        executor=executor,
    )

    payload = build_raw_results_payload(
        plan=plan,
        configuration=configuration,
        provenance=provenance,
        results=results,
    )

    payload[
        "ollama_local_pilot_format_version"
    ] = PILOT_FORMAT_VERSION

    payload[
        "execution_mode"
    ] = "local_ollama"

    payload[
        "research_phase"
    ] = "discovery"

    payload[
        "benchmark_claim_eligible"
    ] = False

    payload[
        "paid_api_used"
    ] = False

    payload[
        "external_api_calls"
    ] = 0

    payload[
        "expected_request_count"
    ] = EXPECTED_REQUEST_COUNT

    payload[
        "order_seed"
    ] = ORDER_SEED

    payload[
        "model_seed"
    ] = MODEL_SEED

    output_path = (
        args.output
        if args.output is not None
        else default_raw_results_path(
            run_id
        )
    )

    write_raw_results_atomic(
        path=output_path,
        payload=payload,
        overwrite=args.overwrite,
    )

    counts = count_result_statuses(
        results
    )

    print()
    print(
        "Local Ollama pilot execution complete."
    )
    print(
        f"Run ID: {run_id}"
    )
    print(
        f"Artifact: {plan.artifact_id}"
    )
    print(
        "Artifact SHA-256: "
        f"{plan.artifact_sha256}"
    )
    print(
        f"Requests: {plan.request_count}"
    )
    print(
        f"Results: {len(results)}"
    )
    print(
        f"Successful: {counts['SUCCESS']}"
    )
    print(
        "Provider errors: "
        f"{counts['PROVIDER_ERROR']}"
    )
    print(
        f"Timeouts: {counts['TIMEOUT']}"
    )
    print(
        "Rate limited: "
        f"{counts['RATE_LIMITED']}"
    )
    print(
        "Invalid responses: "
        f"{counts['INVALID_RESPONSE']}"
    )
    print(
        "Git worktree clean: "
        f"{provenance.worktree_clean}"
    )
    print(
        "Research phase: discovery"
    )
    print(
        "Benchmark claim eligible: False"
    )
    print(
        "Paid API used: False"
    )
    print(
        f"Output: {output_path}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )