import argparse
import json
from pathlib import Path

from sociolinguistic_invariance.evaluation import (
    DEFAULT_SYSTEM_INSTRUCTION,
    EvaluationRun,
    ModelConfiguration,
    evaluation_run_to_dict,
    new_run_id,
    utc_now,
)
from sociolinguistic_invariance.evaluation_plan import (
    build_evaluation_plan,
    evaluation_plan_to_dict,
)
from sociolinguistic_invariance.provenance import (
    capture_git_provenance,
    git_provenance_to_dict,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_ARTIFACT_PATH = Path(
    "data/frozen/pilot_v0.1.jsonl"
)

DEFAULT_MANIFEST_PATH = Path(
    "data/frozen/pilot_v0.1.manifest.json"
)

DEFAULT_RESULTS_DIRECTORY = Path(
    "results/plans"
)


def _default_output_path(
    run_id: str,
) -> Path:
    """Return the default output path for one dry run."""

    return (
        DEFAULT_RESULTS_DIRECTORY
        / f"{run_id}.json"
    )


def _write_json_atomic(
    *,
    path: Path,
    payload: dict[str, object],
    overwrite: bool,
) -> None:
    """Write JSON atomically without accidental overwrite."""

    if path.exists() and not overwrite:
        raise FileExistsError(
            f"Output file already exists: {path}. "
            "Use --overwrite only if replacement is intentional."
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


def _build_parser() -> argparse.ArgumentParser:
    """Construct the dry-run command-line interface."""

    parser = argparse.ArgumentParser(
        description=(
            "Construct and save a provider-neutral "
            "Sociolinguistic Invariance dry-run evaluation plan. "
            "No external model API is contacted."
        )
    )

    parser.add_argument(
        "--artifact",
        type=Path,
        default=DEFAULT_ARTIFACT_PATH,
        help=(
            "Path to the frozen JSONL benchmark artifact."
        ),
    )

    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST_PATH,
        help=(
            "Path to the frozen artifact manifest."
        ),
    )

    parser.add_argument(
        "--provider",
        required=True,
        help=(
            "Provider name to record in the planned model configuration."
        ),
    )

    parser.add_argument(
        "--model",
        dest="requested_model",
        required=True,
        help=(
            "Requested model identifier to record in the plan."
        ),
    )

    parser.add_argument(
        "--temperature",
        type=float,
        default=0.0,
        help="Requested temperature. Default: 0.0.",
    )

    parser.add_argument(
        "--top-p",
        type=float,
        default=None,
        help=(
            "Requested top-p value. "
            "Omit to record the provider default."
        ),
    )

    parser.add_argument(
        "--max-output-tokens",
        type=int,
        default=512,
        help=(
            "Requested maximum output tokens. Default: 512."
        ),
    )

    parser.add_argument(
        "--model-seed",
        type=int,
        default=None,
        help=(
            "Model-generation seed where supported. "
            "Distinct from the request-order seed."
        ),
    )

    parser.add_argument(
        "--system-instruction",
        default=DEFAULT_SYSTEM_INSTRUCTION,
        help=(
            "System instruction to record for the run."
        ),
    )

    parser.add_argument(
        "--sdk-version",
        default=None,
        help=(
            "Provider SDK version to record, if known."
        ),
    )

    parser.add_argument(
        "--randomized",
        action="store_true",
        help=(
            "Randomize prompt ordering deterministically."
        ),
    )

    parser.add_argument(
        "--order-seed",
        type=int,
        default=None,
        help=(
            "Seed controlling prompt ordering. "
            "Required when --randomized is used."
        ),
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=(
            "Optional JSON output path. "
            "Otherwise results/plans/<run_id>.json is used."
        ),
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
        help=(
            "Permit intentional replacement of an existing output file."
        ),
    )

    return parser


def main() -> int:
    """Create and save one dry-run evaluation plan."""

    parser = _build_parser()
    args = parser.parse_args()

    if args.randomized and args.order_seed is None:
        parser.error(
            "--order-seed is required when --randomized is used."
        )

    if not args.randomized and args.order_seed is not None:
        parser.error(
            "--order-seed may only be used together with --randomized."
        )

    provenance = capture_git_provenance(
        REPO_ROOT
    )

    run_id = new_run_id()
    started_at = utc_now()

    configuration = ModelConfiguration(
        provider=args.provider,
        requested_model=args.requested_model,
        temperature=args.temperature,
        top_p=args.top_p,
        max_output_tokens=args.max_output_tokens,
        seed=args.model_seed,
        system_instruction=args.system_instruction,
        sdk_version=args.sdk_version,
    )

    plan = build_evaluation_plan(
        run_id=run_id,
        artifact_path=args.artifact,
        manifest_path=args.manifest,
        randomized=args.randomized,
        order_seed=args.order_seed,
    )

    run = EvaluationRun(
        run_id=run_id,
        artifact_id=plan.artifact_id,
        artifact_path=plan.artifact_path,
        artifact_sha256=plan.artifact_sha256,
        model_configuration=configuration,
        started_at=started_at,
        git_commit=provenance.commit,
    )

    output_path = (
        args.output
        if args.output is not None
        else _default_output_path(run_id)
    )

    payload: dict[str, object] = {
        "artifact_type": "evaluation_dry_run_plan",
        "dry_run": True,
        "manifest_path": args.manifest.as_posix(),
        "git_provenance": git_provenance_to_dict(
            provenance
        ),
        "run": evaluation_run_to_dict(run),
        "plan": evaluation_plan_to_dict(plan),
    }

    _write_json_atomic(
        path=output_path,
        payload=payload,
        overwrite=args.overwrite,
    )

    print("Dry-run evaluation plan created.")
    print(f"Run ID: {run_id}")
    print(f"Artifact: {plan.artifact_id}")
    print(f"Artifact SHA-256: {plan.artifact_sha256}")
    print(f"Provider: {configuration.provider}")
    print(f"Model: {configuration.requested_model}")
    print(f"Randomized: {plan.randomized}")
    print(f"Order seed: {plan.order_seed}")
    print(f"Requests: {plan.request_count}")
    print(f"Git available: {provenance.available}")
    print(f"Git commit: {provenance.commit}")
    print(f"Git worktree clean: {provenance.worktree_clean}")
    print(
        "Git status entries: "
        f"{provenance.status_entry_count}"
    )
    print(f"Output: {output_path}")
    print("External API calls: 0")

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )