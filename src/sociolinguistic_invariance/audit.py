import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sociolinguistic_invariance.core import SemanticFamily, ValidationStatus
from sociolinguistic_invariance.review import ReviewChecklist

REVIEW_PROTOCOL_VERSION = "review-v0.1"


def _family_content_payload(family: SemanticFamily) -> dict[str, Any]:
    """Return the substantive family content used for audit hashing."""

    return {
        "family_id": family.family_id,
        "task_type": family.task_type.value,
        "proposition": family.proposition,
        "domain": family.domain,
        "split": family.split.value,
        "expected_behavior": family.expected_behavior,
        "variants": [
            {
                "condition": variant.condition.value,
                "text": variant.text,
            }
            for variant in family.variants
        ],
    }


def semantic_family_content_hash(family: SemanticFamily) -> str:
    """Return a stable SHA-256 fingerprint of substantive family content."""

    payload = _family_content_payload(family)

    canonical_json = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )

    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class ReviewRecord:
    """Auditable record of one completed human review."""

    family_id: str
    reviewer_id: str
    reviewed_at: datetime
    protocol_version: str
    family_content_sha256: str
    semantic_equivalence: bool
    sociolinguistic_naturalness: bool
    factual_content_preserved: bool
    expected_behavior_clear: bool
    no_prohibited_confounds: bool
    greeklish_verified: bool
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.family_id.strip():
            raise ValueError("family_id must not be empty")

        if not self.reviewer_id.strip():
            raise ValueError("reviewer_id must not be empty")

        if self.reviewed_at.tzinfo is None or self.reviewed_at.utcoffset() is None:
            raise ValueError("reviewed_at must be timezone-aware")

        if len(self.family_content_sha256) != 64:
            raise ValueError("family_content_sha256 must be a SHA-256 hex digest")


def create_review_record(
    family: SemanticFamily,
    checklist: ReviewChecklist,
    *,
    reviewed_at: datetime,
) -> ReviewRecord:
    """Create an audit record for a successfully reviewed family."""

    if family.validation_status is not ValidationStatus.REVIEWED:
        raise ValueError("review records require a reviewed family")

    if not checklist.all_checks_passed:
        raise ValueError("review records require all human-review checks to pass")

    return ReviewRecord(
        family_id=family.family_id,
        reviewer_id=checklist.reviewer_id,
        reviewed_at=reviewed_at,
        protocol_version=REVIEW_PROTOCOL_VERSION,
        family_content_sha256=semantic_family_content_hash(family),
        semantic_equivalence=checklist.semantic_equivalence,
        sociolinguistic_naturalness=checklist.sociolinguistic_naturalness,
        factual_content_preserved=checklist.factual_content_preserved,
        expected_behavior_clear=checklist.expected_behavior_clear,
        no_prohibited_confounds=checklist.no_prohibited_confounds,
        greeklish_verified=checklist.greeklish_verified,
        notes=checklist.notes,
    )


def review_record_to_dict(record: ReviewRecord) -> dict[str, Any]:
    """Convert a review record into a JSON-serializable dictionary."""

    reviewed_at_utc = record.reviewed_at.astimezone(UTC)

    return {
        "family_id": record.family_id,
        "reviewer_id": record.reviewer_id,
        "reviewed_at": reviewed_at_utc.isoformat().replace("+00:00", "Z"),
        "protocol_version": record.protocol_version,
        "family_content_sha256": record.family_content_sha256,
        "checks": {
            "semantic_equivalence": record.semantic_equivalence,
            "sociolinguistic_naturalness": record.sociolinguistic_naturalness,
            "factual_content_preserved": record.factual_content_preserved,
            "expected_behavior_clear": record.expected_behavior_clear,
            "no_prohibited_confounds": record.no_prohibited_confounds,
            "greeklish_verified": record.greeklish_verified,
        },
        "notes": record.notes,
    }


def save_review_record(
    record: ReviewRecord,
    path: str | Path,
) -> None:
    """Write one review record to disk as UTF-8 JSON."""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_path.write_text(
        json.dumps(
            review_record_to_dict(record),
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )