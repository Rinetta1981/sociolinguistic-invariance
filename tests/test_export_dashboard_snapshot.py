from __future__ import annotations

import json
from pathlib import Path

import pytest

import scripts.export_dashboard_snapshot as cli

RUN_ID = "run_test"
ANNOTATOR_ID = "annotator-001"


def _write_annotation_marker(path: Path) -> None:
    """Create a minimal placeholder annotation file."""
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        "{}\n",
        encoding="utf-8",
    )


def test_canonical_annotation_paths_finds_only_matching_files(
    tmp_path: Path,
) -> None:
    annotations_dir = (
        tmp_path
        / "results"
        / "annotations"
    )

    expected_names = [
        (
            f"{RUN_ID}_BR_0001_"
            f"{condition}_"
            f"{ANNOTATOR_ID}.json"
        )
        for condition in (
            "standard",
            "formal",
            "informal",
            "greeklish",
        )
    ]

    for name in expected_names:
        _write_annotation_marker(
            annotations_dir / name
        )

    _write_annotation_marker(
        annotations_dir
        / (
            "different_run_BR_0001_"
            "standard_annotator-001.json"
        )
    )

    _write_annotation_marker(
        annotations_dir
        / (
            f"{RUN_ID}_BR_0001_"
            "standard_annotator-999.json"
        )
    )

    paths = cli.canonical_annotation_paths(
        project_root=tmp_path,
        run_id=RUN_ID,
        annotator_id=ANNOTATOR_ID,
    )

    assert [
        path.name
        for path in paths
    ] == sorted(expected_names)


def test_canonical_annotation_paths_rejects_no_matches(
    tmp_path: Path,
) -> None:
    annotations_dir = (
        tmp_path
        / "results"
        / "annotations"
    )

    annotations_dir.mkdir(
        parents=True,
    )

    with pytest.raises(
        FileNotFoundError,
        match="No annotation files were found",
    ):
        cli.canonical_annotation_paths(
            project_root=tmp_path,
            run_id=RUN_ID,
            annotator_id=ANNOTATOR_ID,
        )


def test_export_dashboard_snapshot_writes_serialized_dataset(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    annotation_paths = [
        tmp_path / "annotation-a.json",
        tmp_path / "annotation-b.json",
    ]

    fake_dataset = object()

    payload = {
        "dashboard_data_format_version": (
            "dashboard-data-v0.1"
        ),
        "run_id": RUN_ID,
        "annotator_id": ANNOTATOR_ID,
        "benchmark_claim_eligible": False,
        "family_count": 1,
        "response_count": 1,
        "families": [
            {
                "family_id": "BR_0001",
                "response_text": (
                    "Ελληνικό κείμενο"
                ),
            }
        ],
    }

    captured: dict[str, object] = {}

    def fake_load_dashboard_dataset(
        paths: list[Path],
        *,
        project_root: Path,
    ) -> object:
        captured["paths"] = list(paths)
        captured["project_root"] = (
            project_root
        )

        return fake_dataset

    def fake_dashboard_dataset_to_dict(
        dataset: object,
    ) -> dict[str, object]:
        assert dataset is fake_dataset
        return payload

    monkeypatch.setattr(
        cli,
        "load_dashboard_dataset",
        fake_load_dashboard_dataset,
    )

    monkeypatch.setattr(
        cli,
        "dashboard_dataset_to_dict",
        fake_dashboard_dataset_to_dict,
    )

    output_path = Path(
        "data/dashboard/test.json"
    )

    destination = (
        cli.export_dashboard_snapshot(
            project_root=tmp_path,
            annotation_paths=annotation_paths,
            output_path=output_path,
        )
    )

    expected_destination = (
        tmp_path
        / "data"
        / "dashboard"
        / "test.json"
    )

    assert destination == (
        expected_destination
    )

    assert captured["paths"] == (
        annotation_paths
    )

    assert captured["project_root"] == (
        tmp_path
    )

    raw_text = (
        destination.read_text(
            encoding="utf-8",
        )
    )

    assert raw_text.endswith("\n")

    assert "Ελληνικό κείμενο" in raw_text

    assert json.loads(
        raw_text
    ) == payload


def test_export_dashboard_snapshot_accepts_absolute_output_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_dataset = object()

    monkeypatch.setattr(
        cli,
        "load_dashboard_dataset",
        lambda paths, *, project_root: (
            fake_dataset
        ),
    )

    monkeypatch.setattr(
        cli,
        "dashboard_dataset_to_dict",
        lambda dataset: {
            "run_id": RUN_ID,
        },
    )

    absolute_output = (
        tmp_path
        / "external"
        / "snapshot.json"
    )

    destination = (
        cli.export_dashboard_snapshot(
            project_root=tmp_path,
            annotation_paths=[
                tmp_path / "annotation.json"
            ],
            output_path=absolute_output,
        )
    )

    assert destination == (
        absolute_output
    )

    assert json.loads(
        destination.read_text(
            encoding="utf-8",
        )
    ) == {
        "run_id": RUN_ID,
    }


def test_parser_defaults_match_discovery_snapshot() -> None:
    parser = cli.build_parser()

    args = parser.parse_args([])

    assert args.run_id == (
        cli.DEFAULT_RUN_ID
    )

    assert args.annotator_id == (
        cli.DEFAULT_ANNOTATOR_ID
    )

    assert args.output == (
        cli.DEFAULT_OUTPUT_PATH
    )


def test_committed_discovery_snapshot_has_expected_results() -> None:
    project_root = Path(__file__).resolve().parents[1]

    snapshot_path = (
        project_root
        / "data"
        / "dashboard"
        / "discovery_v0.1.json"
    )

    payload = json.loads(
        snapshot_path.read_text(
            encoding="utf-8",
        )
    )

    assert payload["run_id"] == (
        "run_5d3a9ef724bd471ca96c9efe76bfc7db"
    )

    assert payload["annotator_id"] == (
        "annotator-001"
    )

    assert (
        payload["benchmark_claim_eligible"]
        is False
    )

    assert payload["family_count"] == 3
    assert payload["response_count"] == 12

    family_outcomes = {
        family["family_id"]: family["family_outcome"]
        for family in payload["families"]
    }

    assert family_outcomes == {
        "FP_0001": "DISPARITY",
        "EU_0001": "DISPARITY",
        "BR_0001": "ROBUST_SUCCESS",
    }

    response_outcomes = {
        (
            family["family_id"],
            response["condition"],
        ): response["response_outcome"]
        for family in payload["families"]
        for response in family["responses"]
    }

    assert response_outcomes[
        ("FP_0001", "greeklish")
    ] == "FAIL"

    assert response_outcomes[
        ("EU_0001", "greeklish")
    ] == "FAIL"

    assert response_outcomes[
        ("BR_0001", "greeklish")
    ] == "PASS"