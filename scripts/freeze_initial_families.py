import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from sociolinguistic_invariance.audit import semantic_family_content_hash
from sociolinguistic_invariance.authoring import semantic_family_to_dict
from sociolinguistic_invariance.core import SemanticFamily, ValidationStatus
from sociolinguistic_invariance.data_io import (
    load_semantic_family,
    validate_semantic_family_record,
)
from sociolinguistic_invariance.review import freeze_family

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DISCOVERY_DIR = PROJECT_ROOT / "data" / "discovery"
REVIEW_DIR = PROJECT_ROOT / "data" / "metadata" / "reviews"
FROZEN_DIR = PROJECT_ROOT / "data" / "frozen"

FROZEN_EXPORT = FROZEN_DIR / "pilot_v0.1.jsonl"
FROZEN_MANIFEST = FROZEN_DIR / "pilot_v0.1.manifest.json"

FREEZE_PROTOCOL_VERSION = "freeze-v0.1"
REVIEW_PROTOCOL_VERSION = "review-v0.1"

FAMILY_IDS = (
    "FP_0001",
    "EU_0001",
    "BR_0001",
)

REQUIRED_CHECKS = (
    "semantic_equivalence",
    "sociolinguistic_naturalness",
    "factual_content_preserved",
    "expected_behavior_clear",
    "no_prohibited_confounds",
    "greeklish_verified",
)


def load_json_object(path: Path) -> dict[str, Any]:
    """Load a JSON object and require string keys."""

    raw: object = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(raw, dict):
        raise ValueError(f"Expected a JSON object in {path}.")

    if not all(isinstance(key, str) for key in raw):
        raise ValueError(f"Expected only string keys in {path}.")

    return cast(dict[str, Any], raw)


def require_string(
    record: dict[str, Any],
    key: str,
    *,
    source: Path,
) -> str:
    """Read one required non-empty string from a JSON record."""

    value = record.get(key)

    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"{source} must contain a non-empty string field {key!r}."
        )

    return value


def verify_review_record(
    family: SemanticFamily,
) -> tuple[str, str]:
    """Verify that a reviewed family still matches its human-review record."""

    review_path = REVIEW_DIR / f"{family.family_id}.review.json"

    if not review_path.exists():
        raise FileNotFoundError(
            f"Missing review record for {family.family_id}: {review_path}"
        )

    record = load_json_object(review_path)

    recorded_family_id = require_string(
        record,
        "family_id",
        source=review_path,
    )

    if recorded_family_id != family.family_id:
        raise ValueError(
            f"Review record family mismatch: expected {family.family_id!r}, "
            f"found {recorded_family_id!r}."
        )

    protocol_version = require_string(
        record,
        "protocol_version",
        source=review_path,
    )

    if protocol_version != REVIEW_PROTOCOL_VERSION:
        raise ValueError(
            f"{family.family_id} uses unsupported review protocol "
            f"{protocol_version!r}."
        )

    reviewer_id = require_string(
        record,
        "reviewer_id",
        source=review_path,
    )

    recorded_hash = require_string(
        record,
        "family_content_sha256",
        source=review_path,
    )

    checks = record.get("checks")

    if not isinstance(checks, dict):
        raise ValueError(
            f"{review_path} must contain a 'checks' object."
        )

    for check_name in REQUIRED_CHECKS:
        if checks.get(check_name) is not True:
            raise ValueError(
                f"{family.family_id} cannot be frozen because review check "
                f"{check_name!r} is not true."
            )

    current_hash = semantic_family_content_hash(family)

    if current_hash != recorded_hash:
        raise ValueError(
            f"{family.family_id} has changed since human review. "
            f"Recorded hash: {recorded_hash}; current hash: {current_hash}."
        )

    return current_hash, reviewer_id


def write_json(
    path: Path,
    payload: dict[str, Any],
) -> None:
    """Write a JSON object as UTF-8."""

    path.parent.mkdir(parents=True, exist_ok=True)

    path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> None:
    """Freeze the reviewed initial pilot families."""

    if FROZEN_EXPORT.exists():
        raise FileExistsError(
            f"Frozen pilot export already exists: {FROZEN_EXPORT}"
        )

    if FROZEN_MANIFEST.exists():
        raise FileExistsError(
            f"Frozen pilot manifest already exists: {FROZEN_MANIFEST}"
        )

    frozen_payloads: dict[str, dict[str, Any]] = {}
    manifest_families: list[dict[str, Any]] = []
    reviewer_ids: set[str] = set()

    for family_id in FAMILY_IDS:
        family_path = DISCOVERY_DIR / f"{family_id}.json"
        family = load_semantic_family(family_path)

        if family.validation_status is not ValidationStatus.REVIEWED:
            raise ValueError(
                f"{family_id} must be reviewed before freezing; "
                f"found {family.validation_status.value!r}."
            )

        content_hash, reviewer_id = verify_review_record(family)

        frozen_family = freeze_family(family)
        frozen_payload = semantic_family_to_dict(frozen_family)

        validate_semantic_family_record(frozen_payload)

        frozen_payloads[family_id] = frozen_payload
        reviewer_ids.add(reviewer_id)

        manifest_families.append(
            {
                "family_id": family_id,
                "split": frozen_family.split.value,
                "task_type": frozen_family.task_type.value,
                "content_sha256": content_hash,
                "review_record": (
                    f"data/metadata/reviews/{family_id}.review.json"
                ),
            }
        )

    frozen_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")

    jsonl_text = "".join(
        json.dumps(
            frozen_payloads[family_id],
            ensure_ascii=False,
            separators=(",", ":"),
        )
        + "\n"
        for family_id in FAMILY_IDS
    )

    export_sha256 = hashlib.sha256(
        jsonl_text.encode("utf-8")
    ).hexdigest()

    manifest: dict[str, Any] = {
        "artifact_id": "pilot_v0.1",
        "artifact_type": "frozen_pilot",
        "claim_boundary": (
            "Initial frozen pilot only; not the full discovery or "
            "confirmatory benchmark."
        ),
        "freeze_protocol_version": FREEZE_PROTOCOL_VERSION,
        "review_protocol_version": REVIEW_PROTOCOL_VERSION,
        "frozen_at": frozen_at,
        "reviewer_ids": sorted(reviewer_ids),
        "family_count": len(FAMILY_IDS),
        "export_file": "data/frozen/pilot_v0.1.jsonl",
        "export_sha256": export_sha256,
        "families": manifest_families,
    }

    FROZEN_DIR.mkdir(parents=True, exist_ok=True)

    for family_id in FAMILY_IDS:
        family_path = DISCOVERY_DIR / f"{family_id}.json"

        write_json(
            family_path,
            frozen_payloads[family_id],
        )

    FROZEN_EXPORT.write_text(
        jsonl_text,
        encoding="utf-8",
    )

    write_json(
        FROZEN_MANIFEST,
        manifest,
    )

    print("Frozen pilot created successfully.")
    print(f"  families: {len(FAMILY_IDS)}")
    print(f"  export:   {FROZEN_EXPORT.relative_to(PROJECT_ROOT)}")
    print(f"  manifest: {FROZEN_MANIFEST.relative_to(PROJECT_ROOT)}")
    print(f"  sha256:   {export_sha256}")


if __name__ == "__main__":
    main()