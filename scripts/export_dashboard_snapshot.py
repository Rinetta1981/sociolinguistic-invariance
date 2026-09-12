from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from sociolinguistic_invariance.dashboard_data import (
    dashboard_dataset_to_dict,
    load_dashboard_dataset,
)

DEFAULT_RUN_ID = "run_5d3a9ef724bd471ca96c9efe76bfc7db"
DEFAULT_ANNOTATOR_ID = "annotator-001"
DEFAULT_OUTPUT_PATH = Path("data/dashboard/discovery_v0.1.json")


def canonical_annotation_paths(
    *,
    project_root: Path,
    run_id: str,
    annotator_id: str,
) -> list[Path]:
    """Return annotation files for one run and annotator."""
    annotation_dir = project_root / "results" / "annotations"

    paths = sorted(
        annotation_dir.glob(
            f"{run_id}_*_{annotator_id}.json"
        )
    )

    if not paths:
        raise FileNotFoundError(
            "No annotation files were found for "
            f"run {run_id!r} and annotator {annotator_id!r}."
        )

    return paths


def export_dashboard_snapshot(
    *,
    project_root: Path,
    annotation_paths: Sequence[Path],
    output_path: Path,
) -> Path:
    """Build, validate, and write a portable dashboard snapshot."""
    dataset = load_dashboard_dataset(
        annotation_paths,
        project_root=project_root,
    )

    payload = dashboard_dataset_to_dict(dataset)

    destination = (
        output_path
        if output_path.is_absolute()
        else project_root / output_path
    )

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    destination.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    return destination


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Export a validated portable dashboard snapshot "
            "from local annotation artifacts."
        )
    )

    parser.add_argument(
        "--run-id",
        default=DEFAULT_RUN_ID,
        help=(
            "Run ID whose annotations should be exported. "
            f"Default: {DEFAULT_RUN_ID}"
        ),
    )

    parser.add_argument(
        "--annotator-id",
        default=DEFAULT_ANNOTATOR_ID,
        help=(
            "Annotator ID whose annotations should be exported. "
            f"Default: {DEFAULT_ANNOTATOR_ID}"
        ),
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help=(
            "Output JSON path relative to the project root. "
            f"Default: {DEFAULT_OUTPUT_PATH}"
        ),
    )

    return parser


def main() -> None:
    """Export the requested dashboard snapshot."""
    args = build_parser().parse_args()

    project_root = Path(__file__).resolve().parents[1]

    annotation_paths = canonical_annotation_paths(
        project_root=project_root,
        run_id=args.run_id,
        annotator_id=args.annotator_id,
    )

    output_path = export_dashboard_snapshot(
        project_root=project_root,
        annotation_paths=annotation_paths,
        output_path=args.output,
    )

    print("Dashboard snapshot exported.")
    print(f"Run ID: {args.run_id}")
    print(f"Annotator ID: {args.annotator_id}")
    print(f"Annotations: {len(annotation_paths)}")
    print(f"Output: {output_path}")


if __name__ == "__main__":
    main()