import argparse
from pathlib import Path
from typing import cast

from sociolinguistic_invariance.annotation_source_export import (
    load_raw_results_artifact,
    prepare_annotation_sources,
    repository_relative_label,
    sha256_file,
    write_annotation_sources_atomic,
)
from sociolinguistic_invariance.provenance import (
    capture_git_provenance,
    require_clean_git_worktree,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_OUTPUT_DIR = (
    REPO_ROOT
    / "results"
    / "annotation_sources"
)


def _build_parser() -> argparse.ArgumentParser:
    """Construct the annotation-source export CLI."""

    parser = argparse.ArgumentParser(
        description=(
            "Split one completed raw evaluation-results "
            "artifact into single-response JSON artifacts "
            "ready for the human annotation workflow."
        )
    )

    parser.add_argument(
        "source",
        type=Path,
        help=(
            "Path to one completed raw evaluation-results "
            "JSON artifact."
        ),
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=(
            "Directory for generated single-response "
            "annotation-source artifacts."
        ),
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
        help=(
            "Explicitly permit replacement of existing "
            "annotation-source artifacts."
        ),
    )

    return parser


def main() -> int:
    """Prepare one completed batch for human annotation."""

    parser = _build_parser()

    args = parser.parse_args()

    source_argument = cast(
        Path,
        args.source,
    )

    output_directory = cast(
        Path,
        args.output_dir,
    )

    overwrite = cast(
        bool,
        args.overwrite,
    )

    source_path = (
        source_argument.resolve()
    )

    if not source_path.exists():
        parser.error(
            "Source artifact does not exist: "
            f"{source_path}"
        )

    provenance = capture_git_provenance(
        REPO_ROOT
    )

    require_clean_git_worktree(
        provenance
    )

    batch = load_raw_results_artifact(
        source_path
    )

    source_sha256 = sha256_file(
        source_path
    )

    source_label = (
        repository_relative_label(
            path=source_path,
            repo_root=REPO_ROOT,
        )
    )

    prepared = prepare_annotation_sources(
        batch=batch,
        source_artifact=source_label,
        source_artifact_sha256=(
            source_sha256
        ),
    )

    output_paths = (
        write_annotation_sources_atomic(
            output_dir=output_directory,
            sources=prepared,
            overwrite=overwrite,
        )
    )

    print(
        "Annotation-source preparation complete."
    )
    print(
        f"Source: {source_label}"
    )
    print(
        f"Source SHA-256: {source_sha256}"
    )
    print(
        f"Prepared responses: {len(prepared)}"
    )
    print(
        f"Written files: {len(output_paths)}"
    )

    if prepared:
        benchmark_claim_eligible = (
            prepared[
                0
            ].payload[
                "benchmark_claim_eligible"
            ]
        )

        print(
            "Benchmark claim eligible: "
            f"{benchmark_claim_eligible}"
        )

    print(
        f"Output directory: {output_directory}"
    )

    print()

    for path in output_paths:
        print(
            repository_relative_label(
                path=path,
                repo_root=REPO_ROOT,
            )
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )