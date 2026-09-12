from __future__ import annotations

import argparse
import os
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from sociolinguistic_invariance.batch_execution import (
    write_raw_results_atomic,
)
from sociolinguistic_invariance.pilot_analysis import (
    analyze_annotation_paths,
    pilot_analysis_to_dict,
)
from sociolinguistic_invariance.pilot_reporting import (
    render_pilot_report,
)

DEFAULT_ANNOTATIONS_DIR = Path(
    "results/annotations"
)
DEFAULT_ANALYSIS_DIR = Path(
    "results/analysis"
)
DEFAULT_REPORTS_DIR = Path(
    "results/reports"
)


@dataclass(
    frozen=True,
    slots=True,
)
class GeneratedPilotOutputs:
    """Paths and metadata for generated pilot outputs."""

    analysis_path: Path
    report_path: Path
    annotation_count: int
    family_count: int
    benchmark_claim_eligible: bool


def discover_annotation_paths(
    *,
    annotations_dir: Path,
    run_id: str,
    annotator_id: str,
) -> tuple[Path, ...]:
    """Find annotation artifacts for one run and annotator."""

    if not annotations_dir.exists():
        raise FileNotFoundError(
            "Annotation directory does not exist: "
            f"{annotations_dir}"
        )

    if not annotations_dir.is_dir():
        raise ValueError(
            "Annotation path is not a directory: "
            f"{annotations_dir}"
        )

    prefix = f"{run_id}_"
    suffix = f"_{annotator_id}.json"

    paths = tuple(
        sorted(
            path
            for path in annotations_dir.iterdir()
            if (
                path.is_file()
                and path.name.startswith(
                    prefix
                )
                and path.name.endswith(
                    suffix
                )
            )
        )
    )

    if not paths:
        raise FileNotFoundError(
            "No annotation artifacts found for "
            f"run {run_id!r} and annotator "
            f"{annotator_id!r} in "
            f"{annotations_dir}."
        )

    return paths


def _write_text_atomic(
    *,
    path: Path,
    text: str,
    overwrite: bool = False,
) -> None:
    """Write UTF-8 text atomically without silent overwrite."""

    if path.exists() and not overwrite:
        raise FileExistsError(
            f"Output already exists: {path}"
        )

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    file_descriptor, temporary_name = (
        tempfile.mkstemp(
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
        )
    )

    temporary_path = Path(
        temporary_name
    )

    try:
        with os.fdopen(
            file_descriptor,
            "w",
            encoding="utf-8",
            newline="\n",
        ) as handle:
            handle.write(
                text
            )
            handle.flush()
            os.fsync(
                handle.fileno()
            )

        if path.exists() and not overwrite:
            raise FileExistsError(
                f"Output already exists: {path}"
            )

        os.replace(
            temporary_path,
            path,
        )
    finally:
        temporary_path.unlink(
            missing_ok=True
        )


def generate_pilot_outputs(
    *,
    run_id: str,
    annotator_id: str,
    annotations_dir: Path = DEFAULT_ANNOTATIONS_DIR,
    analysis_dir: Path = DEFAULT_ANALYSIS_DIR,
    reports_dir: Path = DEFAULT_REPORTS_DIR,
    overwrite: bool = False,
) -> GeneratedPilotOutputs:
    """Generate JSON analysis and Markdown report for one run."""

    if not run_id.strip():
        raise ValueError(
            "run_id must be non-blank."
        )

    if not annotator_id.strip():
        raise ValueError(
            "annotator_id must be non-blank."
        )

    annotation_paths = (
        discover_annotation_paths(
            annotations_dir=annotations_dir,
            run_id=run_id,
            annotator_id=annotator_id,
        )
    )

    analysis = analyze_annotation_paths(
        annotation_paths
    )

    if analysis.run_id != run_id:
        raise ValueError(
            "Loaded annotations do not match "
            f"requested run_id {run_id!r}."
        )

    if analysis.annotator_id != annotator_id:
        raise ValueError(
            "Loaded annotations do not match "
            f"requested annotator_id "
            f"{annotator_id!r}."
        )

    analysis_path = (
        analysis_dir
        / f"{run_id}_analysis.json"
    )

    report_path = (
        reports_dir
        / f"{run_id}_report.md"
    )

    existing_outputs = tuple(
        path
        for path in (
            analysis_path,
            report_path,
        )
        if path.exists()
    )

    if existing_outputs and not overwrite:
        existing_text = ", ".join(
            str(path)
            for path in existing_outputs
        )

        raise FileExistsError(
            "Refusing to overwrite existing "
            f"output(s): {existing_text}. "
            "Use --overwrite to replace them."
        )

    analysis_payload = (
        pilot_analysis_to_dict(
            analysis
        )
    )

    report_text = render_pilot_report(
        analysis
    )

    write_raw_results_atomic(
        path=analysis_path,
        payload=analysis_payload,
        overwrite=overwrite,
    )

    _write_text_atomic(
        path=report_path,
        text=report_text,
        overwrite=overwrite,
    )

    return GeneratedPilotOutputs(
        analysis_path=analysis_path,
        report_path=report_path,
        annotation_count=len(
            analysis.annotations
        ),
        family_count=len(
            analysis.families
        ),
        benchmark_claim_eligible=(
            analysis.benchmark_claim_eligible
        ),
    )


def build_parser(
) -> argparse.ArgumentParser:
    """Build the command-line parser."""

    parser = argparse.ArgumentParser(
        description=(
            "Aggregate human-scored response "
            "annotations and generate a "
            "machine-readable pilot analysis "
            "plus a Markdown research report."
        )
    )

    parser.add_argument(
        "--run-id",
        required=True,
        help="Run ID to analyze.",
    )

    parser.add_argument(
        "--annotator-id",
        required=True,
        help="Annotator ID to analyze.",
    )

    parser.add_argument(
        "--annotations-dir",
        type=Path,
        default=DEFAULT_ANNOTATIONS_DIR,
        help=(
            "Directory containing human "
            "annotation artifacts."
        ),
    )

    parser.add_argument(
        "--analysis-dir",
        type=Path,
        default=DEFAULT_ANALYSIS_DIR,
        help=(
            "Directory for the generated "
            "analysis JSON."
        ),
    )

    parser.add_argument(
        "--reports-dir",
        type=Path,
        default=DEFAULT_REPORTS_DIR,
        help=(
            "Directory for the generated "
            "Markdown report."
        ),
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
        help=(
            "Explicitly replace existing "
            "analysis/report outputs."
        ),
    )

    return parser


def main(
    argv: Sequence[str] | None = None,
) -> int:
    """Run the pilot report generator."""

    parser = build_parser()
    args = parser.parse_args(
        argv
    )

    try:
        outputs = generate_pilot_outputs(
            run_id=args.run_id,
            annotator_id=args.annotator_id,
            annotations_dir=(
                args.annotations_dir
            ),
            analysis_dir=(
                args.analysis_dir
            ),
            reports_dir=(
                args.reports_dir
            ),
            overwrite=args.overwrite,
        )
    except (
        FileExistsError,
        FileNotFoundError,
        ValueError,
    ) as exc:
        parser.error(
            str(
                exc
            )
        )

    print(
        "Pilot analysis complete."
    )
    print(
        "Annotations: "
        f"{outputs.annotation_count}"
    )
    print(
        "Families: "
        f"{outputs.family_count}"
    )
    print(
        "Benchmark claim eligible: "
        f"{outputs.benchmark_claim_eligible}"
    )
    print(
        "Analysis JSON: "
        f"{outputs.analysis_path}"
    )
    print(
        "Markdown report: "
        f"{outputs.report_path}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )