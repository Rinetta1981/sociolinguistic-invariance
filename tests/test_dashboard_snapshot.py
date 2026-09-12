from __future__ import annotations

import json
from pathlib import Path

import pytest

from sociolinguistic_invariance.dashboard_snapshot import (
    load_dashboard_snapshot,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_PATH = (
    PROJECT_ROOT
    / "data"
    / "dashboard"
    / "discovery_v0.1.json"
)


def _snapshot_payload() -> dict[str, object]:
    """Load the committed discovery snapshot as a mutable dictionary."""
    payload = json.loads(
        SNAPSHOT_PATH.read_text(
            encoding="utf-8",
        )
    )

    assert isinstance(payload, dict)

    return payload


def _write_payload(
    tmp_path: Path,
    payload: dict[str, object],
) -> Path:
    """Write a test snapshot and return its path."""
    path = tmp_path / "snapshot.json"

    path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    return path


def test_load_dashboard_snapshot_reads_committed_discovery_snapshot() -> None:
    dataset = load_dashboard_snapshot(
        SNAPSHOT_PATH
    )

    assert dataset.run_id == (
        "run_5d3a9ef724bd471ca96c9efe76bfc7db"
    )

    assert dataset.annotator_id == (
        "annotator-001"
    )

    assert (
        dataset.benchmark_claim_eligible
        is False
    )

    assert dataset.family_count == 3
    assert dataset.response_count == 12

    assert len(dataset.families) == 3

    outcomes = {
        family.family_id: family.family_outcome
        for family in dataset.families
    }

    assert outcomes == {
        "FP_0001": "DISPARITY",
        "EU_0001": "DISPARITY",
        "BR_0001": "ROBUST_SUCCESS",
    }


def test_load_dashboard_snapshot_rejects_unknown_format(
    tmp_path: Path,
) -> None:
    payload = _snapshot_payload()

    payload[
        "dashboard_data_format_version"
    ] = "dashboard-data-v999"

    path = _write_payload(
        tmp_path,
        payload,
    )

    with pytest.raises(
        ValueError,
        match="Unsupported dashboard snapshot format",
    ):
        load_dashboard_snapshot(path)


def test_load_dashboard_snapshot_rejects_response_hash_mismatch(
    tmp_path: Path,
) -> None:
    payload = _snapshot_payload()

    families = payload["families"]

    assert isinstance(families, list)

    first_family = families[0]

    assert isinstance(first_family, dict)

    responses = first_family["responses"]

    assert isinstance(responses, list)

    first_response = responses[0]

    assert isinstance(first_response, dict)

    first_response["response_text"] = (
        "This response has been altered."
    )

    path = _write_payload(
        tmp_path,
        payload,
    )

    with pytest.raises(
        ValueError,
        match="response_sha256 does not match",
    ):
        load_dashboard_snapshot(path)


def test_load_dashboard_snapshot_rejects_family_count_mismatch(
    tmp_path: Path,
) -> None:
    payload = _snapshot_payload()

    payload["family_count"] = 99

    path = _write_payload(
        tmp_path,
        payload,
    )

    with pytest.raises(
        ValueError,
        match="family_count does not match",
    ):
        load_dashboard_snapshot(path)


def test_load_dashboard_snapshot_rejects_response_count_mismatch(
    tmp_path: Path,
) -> None:
    payload = _snapshot_payload()

    payload["response_count"] = 99

    path = _write_payload(
        tmp_path,
        payload,
    )

    with pytest.raises(
        ValueError,
        match="response_count does not match",
    ):
        load_dashboard_snapshot(path)


def test_load_dashboard_snapshot_rejects_duplicate_family_ids(
    tmp_path: Path,
) -> None:
    payload = _snapshot_payload()

    families = payload["families"]

    assert isinstance(families, list)
    assert len(families) >= 2
    assert isinstance(families[0], dict)
    assert isinstance(families[1], dict)

    families[1]["family_id"] = (
        families[0]["family_id"]
    )

    path = _write_payload(
        tmp_path,
        payload,
    )

    with pytest.raises(
        ValueError,
        match="duplicate family IDs",
    ):
        load_dashboard_snapshot(path)


def test_load_dashboard_snapshot_rejects_duplicate_conditions(
    tmp_path: Path,
) -> None:
    payload = _snapshot_payload()

    families = payload["families"]

    assert isinstance(families, list)

    first_family = families[0]

    assert isinstance(first_family, dict)

    responses = first_family["responses"]

    assert isinstance(responses, list)
    assert len(responses) >= 2
    assert isinstance(responses[0], dict)
    assert isinstance(responses[1], dict)

    responses[1]["condition"] = (
        responses[0]["condition"]
    )

    path = _write_payload(
        tmp_path,
        payload,
    )

    with pytest.raises(
        ValueError,
        match="contains duplicate conditions",
    ):
        load_dashboard_snapshot(path)