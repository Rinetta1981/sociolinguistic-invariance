import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]

SCRIPT_PATH = (
    REPO_ROOT
    / "scripts"
    / "run_mock_pilot.py"
)

EXPECTED_ARTIFACT_SHA256 = (
    "ec888b5f47489f7abe029d5fb870feef"
    "0d5e72ccf3afbe7ebbabec558ab3f5b9"
)


def _run_cli(
    *arguments: str,
) -> subprocess.CompletedProcess[str]:
    """Run the mock-pilot CLI."""

    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            *arguments,
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def _load_json(
    path: Path,
) -> dict[str, Any]:
    """Load one JSON artifact."""

    raw_payload = json.loads(
        path.read_text(
            encoding="utf-8",
        )
    )

    assert isinstance(
        raw_payload,
        dict,
    )

    return raw_payload


def test_help_identifies_mock_only_execution() -> None:
    completed = _run_cli(
        "--help"
    )

    assert completed.returncode == 0

    assert (
        "No external model API is contacted."
        in completed.stdout
    )

    assert "--randomized" in completed.stdout
    assert "--order-seed" in completed.stdout
    assert "--output" in completed.stdout


def test_randomized_execution_requires_order_seed() -> None:
    completed = _run_cli(
        "--randomized"
    )

    assert completed.returncode == 2

    assert (
        "--order-seed is required when "
        "--randomized is used."
        in completed.stderr
    )


def test_order_seed_requires_randomized_flag() -> None:
    completed = _run_cli(
        "--order-seed",
        "20260910",
    )

    assert completed.returncode == 2

    assert (
        "--order-seed may only be used together "
        "with --randomized."
        in completed.stderr
    )


def test_cli_creates_complete_fixed_raw_artifact(
    tmp_path: Path,
) -> None:
    output_path = (
        tmp_path
        / "fixed-results.json"
    )

    completed = _run_cli(
        "--output",
        str(output_path),
    )

    assert completed.returncode == 0
    assert output_path.exists()

    payload = _load_json(
        output_path
    )

    assert payload["artifact_type"] == (
        "raw_evaluation_results"
    )

    assert payload[
        "raw_results_format_version"
    ] == "raw-results-v0.1"

    assert payload["artifact_id"] == (
        "pilot_v0.1"
    )

    assert payload["artifact_sha256"] == (
        EXPECTED_ARTIFACT_SHA256
    )

    assert payload["result_count"] == 12

    plan = payload["plan"]

    assert isinstance(
        plan,
        dict,
    )

    assert plan["request_count"] == 12
    assert plan["randomized"] is False
    assert plan["order_seed"] is None

    status_counts = payload[
        "status_counts"
    ]

    assert isinstance(
        status_counts,
        dict,
    )

    assert status_counts == {
        "SUCCESS": 12,
        "PROVIDER_ERROR": 0,
        "TIMEOUT": 0,
        "RATE_LIMITED": 0,
        "INVALID_RESPONSE": 0,
        "SKIPPED": 0,
    }

    assert "External API calls: 0" in (
        completed.stdout
    )


def test_seeded_randomized_runs_have_same_prompt_order(
    tmp_path: Path,
) -> None:
    first_path = (
        tmp_path
        / "first.json"
    )

    second_path = (
        tmp_path
        / "second.json"
    )

    first = _run_cli(
        "--randomized",
        "--order-seed",
        "20260910",
        "--output",
        str(first_path),
    )

    second = _run_cli(
        "--randomized",
        "--order-seed",
        "20260910",
        "--output",
        str(second_path),
    )

    assert first.returncode == 0
    assert second.returncode == 0

    first_payload = _load_json(
        first_path
    )

    second_payload = _load_json(
        second_path
    )

    first_plan = first_payload["plan"]
    second_plan = second_payload["plan"]

    assert isinstance(
        first_plan,
        dict,
    )
    assert isinstance(
        second_plan,
        dict,
    )

    first_requests = first_plan[
        "requests"
    ]

    second_requests = second_plan[
        "requests"
    ]

    assert isinstance(
        first_requests,
        list,
    )
    assert isinstance(
        second_requests,
        list,
    )

    first_order = [
        (
            request["family_id"],
            request["condition"],
        )
        for request in first_requests
    ]

    second_order = [
        (
            request["family_id"],
            request["condition"],
        )
        for request in second_requests
    ]

    assert first_order == second_order


def test_known_seed_has_expected_first_prompt_unit(
    tmp_path: Path,
) -> None:
    output_path = (
        tmp_path
        / "randomized.json"
    )

    completed = _run_cli(
        "--randomized",
        "--order-seed",
        "20260910",
        "--output",
        str(output_path),
    )

    assert completed.returncode == 0

    payload = _load_json(
        output_path
    )

    plan = payload["plan"]

    assert isinstance(
        plan,
        dict,
    )

    requests = plan[
        "requests"
    ]

    assert isinstance(
        requests,
        list,
    )

    first_request = requests[0]

    assert first_request["family_id"] == (
        "BR_0001"
    )

    assert first_request["condition"] == (
        "formal"
    )


def test_mock_results_are_explicitly_marked_as_mock(
    tmp_path: Path,
) -> None:
    output_path = (
        tmp_path
        / "mock-results.json"
    )

    completed = _run_cli(
        "--output",
        str(output_path),
    )

    assert completed.returncode == 0

    payload = _load_json(
        output_path
    )

    results = payload[
        "results"
    ]

    assert isinstance(
        results,
        list,
    )

    assert len(results) == 12

    for result in results:
        assert result["status"] == "SUCCESS"

        response_text = result[
            "response_text"
        ]

        assert isinstance(
            response_text,
            str,
        )

        assert response_text.startswith(
            "[MOCK] No model inference performed"
        )

    provider_request_ids = [
        result["provider_request_id"]
        for result in results
    ]

    assert provider_request_ids == [
        f"mock-{index:04d}"
        for index in range(
            1,
            13,
        )
    ]


def test_run_identity_is_consistent_through_artifact(
    tmp_path: Path,
) -> None:
    output_path = (
        tmp_path
        / "identity.json"
    )

    completed = _run_cli(
        "--output",
        str(output_path),
    )

    assert completed.returncode == 0

    payload = _load_json(
        output_path
    )

    run_id = payload[
        "run_id"
    ]

    plan = payload[
        "plan"
    ]

    results = payload[
        "results"
    ]

    assert isinstance(
        plan,
        dict,
    )

    assert isinstance(
        results,
        list,
    )

    assert plan["run_id"] == run_id

    assert all(
        result["run_id"] == run_id
        for result in results
    )


def test_cli_protects_existing_raw_result(
    tmp_path: Path,
) -> None:
    output_path = (
        tmp_path
        / "protected.json"
    )

    original_text = (
        "do not replace"
    )

    output_path.write_text(
        original_text,
        encoding="utf-8",
    )

    completed = _run_cli(
        "--output",
        str(output_path),
    )

    assert completed.returncode != 0

    assert (
        "Raw result file already exists"
        in completed.stderr
    )

    assert output_path.read_text(
        encoding="utf-8"
    ) == original_text


def test_cli_overwrite_flag_is_explicit(
    tmp_path: Path,
) -> None:
    output_path = (
        tmp_path
        / "overwrite.json"
    )

    output_path.write_text(
        "old content",
        encoding="utf-8",
    )

    completed = _run_cli(
        "--output",
        str(output_path),
        "--overwrite",
    )

    assert completed.returncode == 0

    payload = _load_json(
        output_path
    )

    assert payload["artifact_type"] == (
        "raw_evaluation_results"
    )


def test_raw_artifact_records_git_provenance(
    tmp_path: Path,
) -> None:
    output_path = (
        tmp_path
        / "provenance.json"
    )

    completed = _run_cli(
        "--output",
        str(output_path),
    )

    assert completed.returncode == 0

    payload = _load_json(
        output_path
    )

    provenance = payload[
        "git_provenance"
    ]

    assert isinstance(
        provenance,
        dict,
    )

    assert set(provenance) == {
        "available",
        "commit",
        "worktree_clean",
        "status_entry_count",
        "status_sha256",
    }

    assert provenance[
        "available"
    ] is True

    assert isinstance(
        provenance["worktree_clean"],
        bool,
    )

    assert isinstance(
        provenance["status_entry_count"],
        int,
    )

    status_sha256 = provenance[
        "status_sha256"
    ]

    assert isinstance(
        status_sha256,
        str,
    )

    assert len(
        status_sha256
    ) == 64

    int(
        status_sha256,
        16,
    )