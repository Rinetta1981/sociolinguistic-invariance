import argparse
from pathlib import Path

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
from sociolinguistic_invariance.provenance import (
    capture_git_provenance,
)
from sociolinguistic_invariance.provider import (
    ProviderResponse,
    ScriptedMockProvider,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_ARTIFACT_PATH = Path(
    "data/frozen/pilot_v0.1.jsonl"
)

DEFAULT_MANIFEST_PATH = Path(
    "data/frozen/pilot_v0.1.manifest.json"
)


def _build_parser() -> argparse.ArgumentParser:
    """Construct the mock-pilot command line interface."""

    parser = argparse.ArgumentParser(
        description=(
            "Execute the frozen pilot through the "
            "scripted mock provider and persist raw "
            "provider-neutral results. "
            "No external model API is contacted."
        )
    )

    parser.add_argument(
        "--artifact",
        type=Path,
        default=DEFAULT_ARTIFACT_PATH,
    )

    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST_PATH,
    )

    parser.add_argument(
        "--randomized",
        action="store_true",
    )

    parser.add_argument(
        "--order-seed",
        type=int,
        default=None,
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=None,
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
    )

    return parser


def main() -> int:
    """Execute one complete mock pilot."""

    parser = _build_parser()
    args = parser.parse_args()

    if args.randomized and args.order_seed is None:
        parser.error(
            "--order-seed is required when "
            "--randomized is used."
        )

    if not args.randomized and args.order_seed is not None:
        parser.error(
            "--order-seed may only be used together "
            "with --randomized."
        )

    provenance = capture_git_provenance(
        REPO_ROOT
    )

    run_id = new_run_id()

    plan = build_evaluation_plan(
        run_id=run_id,
        artifact_path=args.artifact,
        manifest_path=args.manifest,
        randomized=args.randomized,
        order_seed=args.order_seed,
    )

    configuration = ModelConfiguration(
        provider="mock",
        requested_model="scripted-mock-v1",
        temperature=0.0,
        top_p=None,
        max_output_tokens=512,
        seed=None,
        system_instruction=(
            "Answer the user's request directly "
            "and accurately."
        ),
        sdk_version=None,
    )

    actions = [
        ProviderResponse(
            text=(
                "[MOCK] No model inference performed "
                f"for {request.family_id}/"
                f"{request.condition.value}."
            ),
            provider_request_id=(
                f"mock-{index:04d}"
            ),
        )
        for index, request in enumerate(
            plan.requests,
            start=1,
        )
    ]

    provider = ScriptedMockProvider(
        provider_name="mock",
        actions=actions,
    )

    executor = EvaluationExecutor(
        provider=provider,
        configuration=configuration,
        retry_policy=RetryPolicy(
            max_attempts=1,
            initial_backoff_seconds=0.0,
            max_backoff_seconds=0.0,
        ),
        sleep_fn=lambda _: None,
    )

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

    print("Mock pilot execution complete.")
    print(f"Run ID: {run_id}")
    print(f"Artifact: {plan.artifact_id}")
    print(
        "Artifact SHA-256: "
        f"{plan.artifact_sha256}"
    )
    print(f"Requests: {plan.request_count}")
    print(f"Results: {len(results)}")
    print(f"Successful: {counts['SUCCESS']}")
    print(
        "Provider errors: "
        f"{counts['PROVIDER_ERROR']}"
    )
    print(f"Timeouts: {counts['TIMEOUT']}")
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
    print(f"Output: {output_path}")
    print("External API calls: 0")

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )