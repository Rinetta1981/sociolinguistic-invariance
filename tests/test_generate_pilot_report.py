import json
from pathlib import Path

import pytest

import scripts.generate_pilot_report as cli
from sociolinguistic_invariance.core import (
    TaskType,
    VariationCondition,
)
from sociolinguistic_invariance.pilot_analysis import (
    AnnotationRecord,
    FamilyAnalysis,
    PilotAnalysis,
)
from sociolinguistic_invariance.scoring import (
    FamilyOutcome,
    ResponseOutcome,
    StandardContrastOutcome,
)

RUN_ID = "run_test"
ANNOTATOR_ID = "annotator-001"


def _analysis() -> PilotAnalysis:
    """Build a minimal complete analysis for CLI tests."""

    response_outcomes = {
        VariationCondition.STANDARD: (
            ResponseOutcome.PASS
        ),
        VariationCondition.FORMAL: (
            ResponseOutcome.PASS
        ),
        VariationCondition.INFORMAL: (
            ResponseOutcome.PASS
        ),
        VariationCondition.GREEKLISH: (
            ResponseOutcome.PASS
        ),
    }

    family = FamilyAnalysis(
        family_id="BR_0001",
        task_type=TaskType.BENIGN_REQUEST,
        rubric_version=(
            "benign-request-rubric-v0.1"
        ),
        response_outcomes=(
            response_outcomes
        ),
        family_outcome=(
            FamilyOutcome.ROBUST_SUCCESS
        ),
        standard_contrasts={
            VariationCondition.FORMAL: (
                StandardContrastOutcome.STABLE_SUCCESS
            ),
            VariationCondition.INFORMAL: (
                StandardContrastOutcome.STABLE_SUCCESS
            ),
            VariationCondition.GREEKLISH: (
                StandardContrastOutcome.STABLE_SUCCESS
            ),
        },
    )

    annotations = tuple(
        AnnotationRecord(
            annotation_artifact=(
                "results/annotations/"
                f"{RUN_ID}_BR_0001_"
                f"{condition.value}_"
                f"{ANNOTATOR_ID}.json"
            ),
            source_artifact=(
                "results/annotation_sources/"
                f"{RUN_ID}_BR_0001_"
                f"{condition.value}.json"
            ),
            source_artifact_type=(
                "single_response_annotation_source"
            ),
            run_id=RUN_ID,
            request_id=(
                f"request_{condition.value}"
            ),
            family_id="BR_0001",
            task_type=(
                TaskType.BENIGN_REQUEST
            ),
            condition=condition,
            response_sha256="a" * 64,
            annotator_id=ANNOTATOR_ID,
            annotation_protocol_version=(
                "annotation-protocol-v0.1"
            ),
            rubric_version=(
                "benign-request-rubric-v0.1"
            ),
            scoring_protocol_version=(
                "scoring-protocol-v0.1"
            ),
            outcome=outcome,
            benchmark_claim_eligible=False,
        )
        for (
            condition,
            outcome,
        ) in response_outcomes.items()
    )

    return PilotAnalysis(
        run_id=RUN_ID,
        annotator_id=ANNOTATOR_ID,
        annotation_protocol_version=(
            "annotation-protocol-v0.1"
        ),
        scoring_protocol_version=(
            "scoring-protocol-v0.1"
        ),
        benchmark_claim_eligible=False,
        annotations=annotations,
        families=(
            family,
        ),
    )


def _annotation_directory(
    tmp_path: Path,
) -> Path:
    """Create matching placeholder annotation files."""

    annotations_dir = (
        tmp_path
        / "annotations"
    )

    annotations_dir.mkdir()

    for condition in (
        "standard",
        "formal",
        "informal",
        "greeklish",
    ):
        path = (
            annotations_dir
            / (
                f"{RUN_ID}_BR_0001_"
                f"{condition}_"
                f"{ANNOTATOR_ID}.json"
            )
        )

        path.write_text(
            "{}",
            encoding="utf-8",
        )

    return annotations_dir


def test_discover_annotation_paths_finds_matching_files(
    tmp_path: Path,
) -> None:
    annotations_dir = (
        _annotation_directory(
            tmp_path
        )
    )

    unrelated = (
        annotations_dir
        / "different_run_BR_0001_standard_"
        "annotator-001.json"
    )

    unrelated.write_text(
        "{}",
        encoding="utf-8",
    )

    paths = (
        cli.discover_annotation_paths(
            annotations_dir=annotations_dir,
            run_id=RUN_ID,
            annotator_id=ANNOTATOR_ID,
        )
    )

    assert len(
        paths
    ) == 4

    assert all(
        path.name.startswith(
            f"{RUN_ID}_"
        )
        for path in paths
    )

    assert all(
        path.name.endswith(
            f"_{ANNOTATOR_ID}.json"
        )
        for path in paths
    )


def test_discover_annotation_paths_rejects_no_matches(
    tmp_path: Path,
) -> None:
    annotations_dir = (
        tmp_path
        / "annotations"
    )

    annotations_dir.mkdir()

    with pytest.raises(
        FileNotFoundError,
        match="No annotation artifacts found",
    ):
        cli.discover_annotation_paths(
            annotations_dir=annotations_dir,
            run_id=RUN_ID,
            annotator_id=ANNOTATOR_ID,
        )


def test_atomic_text_writer_writes_text(
    tmp_path: Path,
) -> None:
    path = (
        tmp_path
        / "report.md"
    )

    cli._write_text_atomic(
        path=path,
        text="# Report\n",
    )

    assert (
        path.read_text(
            encoding="utf-8"
        )
        == "# Report\n"
    )


def test_atomic_text_writer_rejects_silent_overwrite(
    tmp_path: Path,
) -> None:
    path = (
        tmp_path
        / "report.md"
    )

    path.write_text(
        "original",
        encoding="utf-8",
    )

    with pytest.raises(
        FileExistsError,
        match="already exists",
    ):
        cli._write_text_atomic(
            path=path,
            text="replacement",
        )

    assert (
        path.read_text(
            encoding="utf-8"
        )
        == "original"
    )


def test_atomic_text_writer_allows_explicit_overwrite(
    tmp_path: Path,
) -> None:
    path = (
        tmp_path
        / "report.md"
    )

    path.write_text(
        "original",
        encoding="utf-8",
    )

    cli._write_text_atomic(
        path=path,
        text="replacement",
        overwrite=True,
    )

    assert (
        path.read_text(
            encoding="utf-8"
        )
        == "replacement"
    )


def test_generate_pilot_outputs_writes_json_and_markdown(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    annotations_dir = (
        _annotation_directory(
            tmp_path
        )
    )

    analysis_dir = (
        tmp_path
        / "analysis"
    )

    reports_dir = (
        tmp_path
        / "reports"
    )

    analysis = _analysis()

    monkeypatch.setattr(
        cli,
        "analyze_annotation_paths",
        lambda paths: analysis,
    )

    outputs = (
        cli.generate_pilot_outputs(
            run_id=RUN_ID,
            annotator_id=ANNOTATOR_ID,
            annotations_dir=(
                annotations_dir
            ),
            analysis_dir=analysis_dir,
            reports_dir=reports_dir,
        )
    )

    assert (
        outputs.analysis_path
        == (
            analysis_dir
            / f"{RUN_ID}_analysis.json"
        )
    )

    assert (
        outputs.report_path
        == (
            reports_dir
            / f"{RUN_ID}_report.md"
        )
    )

    assert (
        outputs.annotation_count
        == 4
    )

    assert (
        outputs.family_count
        == 1
    )

    assert (
        outputs.benchmark_claim_eligible
        is False
    )

    payload = json.loads(
        outputs.analysis_path.read_text(
            encoding="utf-8"
        )
    )

    assert (
        payload[
            "run_id"
        ]
        == RUN_ID
    )

    assert (
        payload[
            "response_count"
        ]
        == 4
    )

    assert (
        payload[
            "family_count"
        ]
        == 1
    )

    report = (
        outputs.report_path.read_text(
            encoding="utf-8"
        )
    )

    assert (
        "# Sociolinguistic Invariance — "
        "Discovery Pilot Report"
        in report
    )

    assert (
        "benchmark_claim_eligible=false"
        in report
    )

    assert (
        "**ROBUST_SUCCESS**"
        in report
    )


def test_generate_pilot_outputs_rejects_existing_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    annotations_dir = (
        _annotation_directory(
            tmp_path
        )
    )

    analysis_dir = (
        tmp_path
        / "analysis"
    )

    reports_dir = (
        tmp_path
        / "reports"
    )

    analysis_dir.mkdir()
    reports_dir.mkdir()

    analysis_path = (
        analysis_dir
        / f"{RUN_ID}_analysis.json"
    )

    report_path = (
        reports_dir
        / f"{RUN_ID}_report.md"
    )

    analysis_path.write_text(
        "existing analysis",
        encoding="utf-8",
    )

    report_path.write_text(
        "existing report",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        cli,
        "analyze_annotation_paths",
        lambda paths: _analysis(),
    )

    with pytest.raises(
        FileExistsError,
        match="Refusing to overwrite",
    ):
        cli.generate_pilot_outputs(
            run_id=RUN_ID,
            annotator_id=ANNOTATOR_ID,
            annotations_dir=(
                annotations_dir
            ),
            analysis_dir=analysis_dir,
            reports_dir=reports_dir,
        )

    assert (
        analysis_path.read_text(
            encoding="utf-8"
        )
        == "existing analysis"
    )

    assert (
        report_path.read_text(
            encoding="utf-8"
        )
        == "existing report"
    )


def test_generate_pilot_outputs_allows_explicit_overwrite(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    annotations_dir = (
        _annotation_directory(
            tmp_path
        )
    )

    analysis_dir = (
        tmp_path
        / "analysis"
    )

    reports_dir = (
        tmp_path
        / "reports"
    )

    analysis_dir.mkdir()
    reports_dir.mkdir()

    analysis_path = (
        analysis_dir
        / f"{RUN_ID}_analysis.json"
    )

    report_path = (
        reports_dir
        / f"{RUN_ID}_report.md"
    )

    analysis_path.write_text(
        "old analysis",
        encoding="utf-8",
    )

    report_path.write_text(
        "old report",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        cli,
        "analyze_annotation_paths",
        lambda paths: _analysis(),
    )

    outputs = (
        cli.generate_pilot_outputs(
            run_id=RUN_ID,
            annotator_id=ANNOTATOR_ID,
            annotations_dir=(
                annotations_dir
            ),
            analysis_dir=analysis_dir,
            reports_dir=reports_dir,
            overwrite=True,
        )
    )

    payload = json.loads(
        outputs.analysis_path.read_text(
            encoding="utf-8"
        )
    )

    assert (
        payload[
            "run_id"
        ]
        == RUN_ID
    )

    report = (
        outputs.report_path.read_text(
            encoding="utf-8"
        )
    )

    assert (
        "Discovery Pilot Report"
        in report
    )

    assert (
        report
        != "old report"
    )