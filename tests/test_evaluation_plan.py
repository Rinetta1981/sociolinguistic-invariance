import json
from pathlib import Path

import pytest

from sociolinguistic_invariance.core import ValidationStatus
from sociolinguistic_invariance.evaluation import sha256_text
from sociolinguistic_invariance.evaluation_plan import (
    FrozenArtifactManifest,
    build_evaluation_plan,
    evaluation_plan_to_dict,
    load_frozen_families,
    load_frozen_manifest,
    sha256_file,
    verify_frozen_artifact,
)

ARTIFACT_PATH = Path(
    "data/frozen/pilot_v0.1.jsonl"
)
MANIFEST_PATH = Path(
    "data/frozen/pilot_v0.1.manifest.json"
)

EXPECTED_ARTIFACT_SHA256 = (
    "ec888b5f47489f7abe029d5fb870feef"
    "0d5e72ccf3afbe7ebbabec558ab3f5b9"
)

EXPECTED_FIXED_ORDER = (
    ("FP_0001", "standard"),
    ("FP_0001", "formal"),
    ("FP_0001", "informal"),
    ("FP_0001", "greeklish"),
    ("EU_0001", "standard"),
    ("EU_0001", "formal"),
    ("EU_0001", "informal"),
    ("EU_0001", "greeklish"),
    ("BR_0001", "standard"),
    ("BR_0001", "formal"),
    ("BR_0001", "informal"),
    ("BR_0001", "greeklish"),
)


def _load_manifest_record() -> dict[str, object]:
    raw_record = json.loads(
        MANIFEST_PATH.read_text(
            encoding="utf-8",
        )
    )

    assert isinstance(
        raw_record,
        dict,
    )

    return raw_record


def _write_manifest(
    tmp_path: Path,
    **updates: object,
) -> Path:
    record = _load_manifest_record()
    record.update(
        updates
    )

    path = tmp_path / "manifest.json"

    path.write_text(
        json.dumps(
            record,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    return path


def _artifact_lines() -> list[str]:
    return ARTIFACT_PATH.read_text(
        encoding="utf-8",
    ).splitlines()


def _write_artifact(
    tmp_path: Path,
    lines: list[str],
) -> Path:
    path = tmp_path / "artifact.jsonl"

    path.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    return path


def test_load_real_manifest() -> None:
    manifest = load_frozen_manifest(
        MANIFEST_PATH
    )

    assert manifest == FrozenArtifactManifest(
        artifact_id="pilot_v0.1",
        export_file="data/frozen/pilot_v0.1.jsonl",
        export_sha256=EXPECTED_ARTIFACT_SHA256,
        family_count=3,
        freeze_protocol_version="freeze-v0.1",
        review_protocol_version="review-v0.1",
    )


def test_sha256_file_matches_frozen_manifest() -> None:
    assert (
        sha256_file(ARTIFACT_PATH)
        == EXPECTED_ARTIFACT_SHA256
    )


def test_verify_real_frozen_artifact() -> None:
    manifest = verify_frozen_artifact(
        artifact_path=ARTIFACT_PATH,
        manifest_path=MANIFEST_PATH,
    )

    assert manifest.artifact_id == "pilot_v0.1"
    assert manifest.family_count == 3
    assert (
        manifest.export_sha256
        == EXPECTED_ARTIFACT_SHA256
    )


def test_load_real_frozen_families() -> None:
    families = load_frozen_families(
        ARTIFACT_PATH
    )

    assert len(families) == 3
    assert tuple(
        family.family_id
        for family in families
    ) == (
        "FP_0001",
        "EU_0001",
        "BR_0001",
    )

    assert all(
        family.validation_status
        is ValidationStatus.FROZEN
        for family in families
    )


def test_fixed_plan_contains_exactly_twelve_requests() -> None:
    plan = build_evaluation_plan(
        run_id="run_fixed_test",
        artifact_path=ARTIFACT_PATH,
        manifest_path=MANIFEST_PATH,
        randomized=False,
        order_seed=None,
    )

    assert plan.artifact_id == "pilot_v0.1"
    assert plan.request_count == 12
    assert plan.randomized is False
    assert plan.order_seed is None
    assert (
        plan.artifact_sha256
        == EXPECTED_ARTIFACT_SHA256
    )


def test_fixed_plan_has_expected_order() -> None:
    plan = build_evaluation_plan(
        run_id="run_fixed_test",
        artifact_path=ARTIFACT_PATH,
        manifest_path=MANIFEST_PATH,
        randomized=False,
        order_seed=None,
    )

    actual_order = tuple(
        (
            request.family_id,
            request.condition.value,
        )
        for request in plan.requests
    )

    assert actual_order == EXPECTED_FIXED_ORDER


def test_fixed_plan_order_indexes_are_contiguous() -> None:
    plan = build_evaluation_plan(
        run_id="run_fixed_test",
        artifact_path=ARTIFACT_PATH,
        manifest_path=MANIFEST_PATH,
        randomized=False,
        order_seed=None,
    )

    assert tuple(
        request.order_index
        for request in plan.requests
    ) == tuple(
        range(12)
    )


def test_plan_request_ids_are_unique() -> None:
    plan = build_evaluation_plan(
        run_id="run_fixed_test",
        artifact_path=ARTIFACT_PATH,
        manifest_path=MANIFEST_PATH,
        randomized=False,
        order_seed=None,
    )

    request_ids = [
        request.request_id
        for request in plan.requests
    ]

    assert len(
        set(request_ids)
    ) == 12


def test_plan_requests_preserve_exact_prompt_hashes() -> None:
    plan = build_evaluation_plan(
        run_id="run_fixed_test",
        artifact_path=ARTIFACT_PATH,
        manifest_path=MANIFEST_PATH,
        randomized=False,
        order_seed=None,
    )

    for request in plan.requests:
        assert (
            request.prompt_sha256
            == sha256_text(
                request.prompt_text
            )
        )


def test_same_seed_produces_same_randomized_order() -> None:
    first = build_evaluation_plan(
        run_id="run_random_a",
        artifact_path=ARTIFACT_PATH,
        manifest_path=MANIFEST_PATH,
        randomized=True,
        order_seed=20260910,
    )

    second = build_evaluation_plan(
        run_id="run_random_b",
        artifact_path=ARTIFACT_PATH,
        manifest_path=MANIFEST_PATH,
        randomized=True,
        order_seed=20260910,
    )

    first_order = tuple(
        (
            request.family_id,
            request.condition.value,
        )
        for request in first.requests
    )

    second_order = tuple(
        (
            request.family_id,
            request.condition.value,
        )
        for request in second.requests
    )

    assert first_order == second_order


def test_randomized_order_differs_from_fixed_order() -> None:
    plan = build_evaluation_plan(
        run_id="run_random_test",
        artifact_path=ARTIFACT_PATH,
        manifest_path=MANIFEST_PATH,
        randomized=True,
        order_seed=20260910,
    )

    randomized_order = tuple(
        (
            request.family_id,
            request.condition.value,
        )
        for request in plan.requests
    )

    assert randomized_order != EXPECTED_FIXED_ORDER


def test_randomized_plan_preserves_all_prompt_units() -> None:
    plan = build_evaluation_plan(
        run_id="run_random_test",
        artifact_path=ARTIFACT_PATH,
        manifest_path=MANIFEST_PATH,
        randomized=True,
        order_seed=20260910,
    )

    actual_units = {
        (
            request.family_id,
            request.condition.value,
        )
        for request in plan.requests
    }

    assert actual_units == set(
        EXPECTED_FIXED_ORDER
    )


def test_randomized_plan_requires_seed() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "Randomized evaluation requires "
            "an order_seed"
        ),
    ):
        build_evaluation_plan(
            run_id="run_test",
            artifact_path=ARTIFACT_PATH,
            manifest_path=MANIFEST_PATH,
            randomized=True,
            order_seed=None,
        )


def test_plan_rejects_blank_run_id() -> None:
    with pytest.raises(
        ValueError,
        match="run_id must be non-blank",
    ):
        build_evaluation_plan(
            run_id="   ",
            artifact_path=ARTIFACT_PATH,
            manifest_path=MANIFEST_PATH,
            randomized=False,
            order_seed=None,
        )


def test_corrupted_artifact_fails_hash_verification(
    tmp_path: Path,
) -> None:
    corrupted_path = tmp_path / "corrupted.jsonl"

    corrupted_path.write_bytes(
        ARTIFACT_PATH.read_bytes()
        + b"\n"
    )

    with pytest.raises(
        ValueError,
        match="Frozen artifact SHA-256 mismatch",
    ):
        verify_frozen_artifact(
            artifact_path=corrupted_path,
            manifest_path=MANIFEST_PATH,
        )


def test_manifest_family_count_mismatch_is_rejected(
    tmp_path: Path,
) -> None:
    manifest_path = _write_manifest(
        tmp_path,
        family_count=4,
    )

    with pytest.raises(
        ValueError,
        match=(
            "Frozen family count does not "
            "match manifest"
        ),
    ):
        build_evaluation_plan(
            run_id="run_test",
            artifact_path=ARTIFACT_PATH,
            manifest_path=manifest_path,
            randomized=False,
            order_seed=None,
        )


@pytest.mark.parametrize(
    "field_name",
    [
        "artifact_id",
        "export_file",
        "export_sha256",
        "freeze_protocol_version",
        "review_protocol_version",
    ],
)
def test_manifest_rejects_missing_required_string_fields(
    tmp_path: Path,
    field_name: str,
) -> None:
    record = _load_manifest_record()
    record.pop(
        field_name
    )

    path = tmp_path / "manifest.json"

    path.write_text(
        json.dumps(
            record,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="must be a non-blank string",
    ):
        load_frozen_manifest(
            path
        )


def test_manifest_rejects_non_object_json(
    tmp_path: Path,
) -> None:
    path = tmp_path / "manifest.json"

    path.write_text(
        "[]",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match=(
            "Frozen artifact manifest must "
            "contain a JSON object"
        ),
    ):
        load_frozen_manifest(
            path
        )


def test_manifest_rejects_boolean_family_count(
    tmp_path: Path,
) -> None:
    path = _write_manifest(
        tmp_path,
        family_count=True,
    )

    with pytest.raises(
        ValueError,
        match=(
            "Manifest field 'family_count' "
            "must be an integer"
        ),
    ):
        load_frozen_manifest(
            path
        )


@pytest.mark.parametrize(
    "family_count",
    [
        0,
        -1,
    ],
)
def test_manifest_rejects_nonpositive_family_count(
    tmp_path: Path,
    family_count: int,
) -> None:
    path = _write_manifest(
        tmp_path,
        family_count=family_count,
    )

    with pytest.raises(
        ValueError,
        match=(
            "Manifest field 'family_count' "
            "must be positive"
        ),
    ):
        load_frozen_manifest(
            path
        )


def test_manifest_rejects_short_sha256(
    tmp_path: Path,
) -> None:
    path = _write_manifest(
        tmp_path,
        export_sha256="abc",
    )

    with pytest.raises(
        ValueError,
        match=(
            "export_sha256 must contain "
            "exactly 64 hexadecimal characters"
        ),
    ):
        load_frozen_manifest(
            path
        )


def test_manifest_rejects_uppercase_sha256(
    tmp_path: Path,
) -> None:
    path = _write_manifest(
        tmp_path,
        export_sha256="A" * 64,
    )

    with pytest.raises(
        ValueError,
        match=(
            "export_sha256 must be "
            "lowercase hexadecimal"
        ),
    ):
        load_frozen_manifest(
            path
        )


def test_frozen_loader_rejects_blank_line(
    tmp_path: Path,
) -> None:
    lines = _artifact_lines()

    path = _write_artifact(
        tmp_path,
        [
            lines[0],
            "",
            *lines[1:],
        ],
    )

    with pytest.raises(
        ValueError,
        match=(
            "Frozen artifact contains a blank "
            "line at line 2"
        ),
    ):
        load_frozen_families(
            path
        )


def test_frozen_loader_rejects_invalid_json(
    tmp_path: Path,
) -> None:
    path = _write_artifact(
        tmp_path,
        [
            '{"broken":',
        ],
    )

    with pytest.raises(
        ValueError,
        match=(
            "Invalid JSON in frozen artifact "
            "at line 1"
        ),
    ):
        load_frozen_families(
            path
        )


def test_frozen_loader_rejects_non_object_json(
    tmp_path: Path,
) -> None:
    path = _write_artifact(
        tmp_path,
        [
            '["not", "an", "object"]',
        ],
    )

    with pytest.raises(
        ValueError,
        match=(
            "Frozen artifact line 1 must "
            "contain a JSON object"
        ),
    ):
        load_frozen_families(
            path
        )


def test_frozen_loader_rejects_duplicate_family_id(
    tmp_path: Path,
) -> None:
    lines = _artifact_lines()

    path = _write_artifact(
        tmp_path,
        [
            lines[0],
            lines[0],
        ],
    )

    with pytest.raises(
        ValueError,
        match=(
            "Duplicate semantic family ID "
            "in frozen artifact"
        ),
    ):
        load_frozen_families(
            path
        )


def test_frozen_loader_rejects_nonfrozen_family(
    tmp_path: Path,
) -> None:
    record = json.loads(
        _artifact_lines()[0]
    )

    assert isinstance(
        record,
        dict,
    )

    record["validation_status"] = "draft"

    path = _write_artifact(
        tmp_path,
        [
            json.dumps(
                record,
                ensure_ascii=False,
            )
        ],
    )

    with pytest.raises(
        ValueError,
        match="is not frozen",
    ):
        load_frozen_families(
            path
        )


def test_frozen_loader_rejects_empty_artifact(
    tmp_path: Path,
) -> None:
    path = tmp_path / "empty.jsonl"

    path.write_text(
        "",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match=(
            "Frozen artifact contains no "
            "semantic families"
        ),
    ):
        load_frozen_families(
            path
        )


def test_evaluation_plan_serializes_deterministically() -> None:
    plan = build_evaluation_plan(
        run_id="run_serialization_test",
        artifact_path=ARTIFACT_PATH,
        manifest_path=MANIFEST_PATH,
        randomized=False,
        order_seed=None,
    )

    payload = evaluation_plan_to_dict(
        plan
    )

    assert payload["run_id"] == (
        "run_serialization_test"
    )
    assert payload["artifact_id"] == "pilot_v0.1"
    assert payload["artifact_path"] == (
        "data/frozen/pilot_v0.1.jsonl"
    )
    assert payload["artifact_sha256"] == (
        EXPECTED_ARTIFACT_SHA256
    )
    assert payload["randomized"] is False
    assert payload["order_seed"] is None
    assert payload["request_count"] == 12

    requests = payload["requests"]

    assert isinstance(
        requests,
        list,
    )
    assert len(requests) == 12

    first_request = requests[0]

    assert first_request["order_index"] == 0
    assert first_request["family_id"] == "FP_0001"
    assert first_request["task_type"] == (
        "false_premise_correction"
    )
    assert first_request["condition"] == "standard"
    assert first_request["prompt_sha256"] == (
        sha256_text(
            first_request["prompt_text"]
        )
    )