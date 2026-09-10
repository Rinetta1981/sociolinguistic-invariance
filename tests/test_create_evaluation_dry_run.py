import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]

SCRIPT_PATH = (
    REPO_ROOT
    / "scripts"
    / "create_evaluation_dry_run.py"
)

EXPECTED_ARTIFACT_SHA256 = (
    "ec888b5f47489f7abe029d5fb870feef"
    "0d5e72ccf3afbe7ebbabec558ab3f5b9"
)


def _run_cli(
    *arguments: str,
) -> subprocess.CompletedProcess[str]:
    """Run the dry-run CLI using the active test interpreter."""

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
    """Load one generated JSON object."""

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


def test_help_succeeds_and_identifies_dry_run() -> None:
    completed = _run_cli(
        "--help",
    )

    assert completed.returncode == 0

    assert (
        "No external model API is contacted."
        in completed.stdout
    )

    assert "--provider" in completed.stdout
    assert "--model" in completed.stdout
    assert "--randomized" in completed.stdout
    assert "--order-seed" in completed.stdout


def test_randomized_run_requires_order_seed() -> None:
    completed = _run_cli(
        "--provider",
        "example-provider",
        "--model",
        "example-model",
        "--randomized",
    )

    assert completed.returncode == 2

    assert (
        "--order-seed is required when "
        "--randomized is used."
        in completed.stderr
    )


def test_order_seed_requires_randomized_flag() -> None:
    completed = _run_cli(
        "--provider",
        "example-provider",
        "--model",
        "example-model",
        "--order-seed",
        "20260910",
    )

    assert completed.returncode == 2

    assert (
        "--order-seed may only be used together "
        "with --randomized."
        in completed.stderr
    )


def test_cli_creates_fixed_order_plan(
    tmp_path: Path,
) -> None:
    output_path = (
        tmp_path
        / "fixed-plan.json"
    )

    completed = _run_cli(
        "--provider",
        "example-provider",
        "--model",
        "example-model",
        "--output",
        str(output_path),
    )

    assert completed.returncode == 0
    assert output_path.exists()

    payload = _load_json(
        output_path
    )

    assert payload["artifact_type"] == (
        "evaluation_dry_run_plan"
    )
    assert payload["dry_run"] is True

    run = payload["run"]
    plan = payload["plan"]

    assert isinstance(
        run,
        dict,
    )
    assert isinstance(
        plan,
        dict,
    )

    assert run["artifact_id"] == "pilot_v0.1"
    assert run["artifact_sha256"] == (
        EXPECTED_ARTIFACT_SHA256
    )

    configuration = run[
        "model_configuration"
    ]

    assert isinstance(
        configuration,
        dict,
    )

    assert configuration["provider"] == (
        "example-provider"
    )
    assert configuration["requested_model"] == (
        "example-model"
    )

    assert plan["request_count"] == 12
    assert plan["randomized"] is False
    assert plan["order_seed"] is None

    assert "External API calls: 0" in (
        completed.stdout
    )


def test_cli_creates_seeded_randomized_plan(
    tmp_path: Path,
) -> None:
    output_path = (
        tmp_path
        / "randomized-plan.json"
    )

    completed = _run_cli(
        "--provider",
        "example-provider",
        "--model",
        "example-model",
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

    assert plan["request_count"] == 12
    assert plan["randomized"] is True
    assert plan["order_seed"] == 20260910

    requests = plan["requests"]

    assert isinstance(
        requests,
        list,
    )
    assert len(requests) == 12

    request_ids = [
        request["request_id"]
        for request in requests
    ]

    assert len(
        set(request_ids)
    ) == 12


def test_seeded_cli_order_is_reproducible(
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
        "--provider",
        "example-provider",
        "--model",
        "example-model",
        "--randomized",
        "--order-seed",
        "20260910",
        "--output",
        str(first_path),
    )

    second = _run_cli(
        "--provider",
        "example-provider",
        "--model",
        "example-model",
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


def test_cli_records_custom_model_configuration(
    tmp_path: Path,
) -> None:
    output_path = (
        tmp_path
        / "configuration.json"
    )

    completed = _run_cli(
        "--provider",
        "example-provider",
        "--model",
        "example-model",
        "--temperature",
        "0.2",
        "--top-p",
        "0.8",
        "--max-output-tokens",
        "256",
        "--model-seed",
        "42",
        "--system-instruction",
        "Test system instruction.",
        "--sdk-version",
        "9.9.9",
        "--output",
        str(output_path),
    )

    assert completed.returncode == 0

    payload = _load_json(
        output_path
    )

    run = payload["run"]

    assert isinstance(
        run,
        dict,
    )

    configuration = run[
        "model_configuration"
    ]

    assert isinstance(
        configuration,
        dict,
    )

    assert configuration == {
        "provider": "example-provider",
        "requested_model": "example-model",
        "temperature": 0.2,
        "top_p": 0.8,
        "max_output_tokens": 256,
        "seed": 42,
        "system_instruction": (
            "Test system instruction."
        ),
        "sdk_version": "9.9.9",
    }


def test_cli_protects_existing_output_file(
    tmp_path: Path,
) -> None:
    output_path = (
        tmp_path
        / "protected.json"
    )

    original_text = (
        "do not overwrite"
    )

    output_path.write_text(
        original_text,
        encoding="utf-8",
    )

    completed = _run_cli(
        "--provider",
        "example-provider",
        "--model",
        "example-model",
        "--output",
        str(output_path),
    )

    assert completed.returncode != 0

    assert (
        "Output file already exists"
        in completed.stderr
    )

    assert (
        output_path.read_text(
            encoding="utf-8",
        )
        == original_text
    )


def test_cli_overwrite_flag_replaces_existing_output(
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
        "--provider",
        "example-provider",
        "--model",
        "example-model",
        "--output",
        str(output_path),
        "--overwrite",
    )

    assert completed.returncode == 0

    payload = _load_json(
        output_path
    )

    assert payload["dry_run"] is True


def test_cli_records_git_provenance(
    tmp_path: Path,
) -> None:
    output_path = (
        tmp_path
        / "provenance.json"
    )

    completed = _run_cli(
        "--provider",
        "example-provider",
        "--model",
        "example-model",
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

    assert provenance["available"] is True

    commit = provenance[
        "commit"
    ]

    assert isinstance(
        commit,
        str,
    )
    assert len(commit) in {
        40,
        64,
    }

    int(
        commit,
        16,
    )

    worktree_clean = provenance[
        "worktree_clean"
    ]

    assert isinstance(
        worktree_clean,
        bool,
    )

    status_entry_count = provenance[
        "status_entry_count"
    ]

    assert isinstance(
        status_entry_count,
        int,
    )
    assert status_entry_count >= 0

    status_sha256 = provenance[
        "status_sha256"
    ]

    assert isinstance(
        status_sha256,
        str,
    )
    assert len(status_sha256) == 64

    int(
        status_sha256,
        16,
    )

    assert worktree_clean is (
        status_entry_count == 0
    )

    run = payload[
        "run"
    ]

    assert isinstance(
        run,
        dict,
    )

    assert run["git_commit"] == commit

    assert "Git available: True" in (
        completed.stdout
    )
    assert "Git worktree clean:" in (
        completed.stdout
    )
    assert "Git status entries:" in (
        completed.stdout
    )


def test_git_provenance_does_not_expose_status_paths(
    tmp_path: Path,
) -> None:
    output_path = (
        tmp_path
        / "provenance-privacy.json"
    )

    completed = _run_cli(
        "--provider",
        "example-provider",
        "--model",
        "example-model",
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