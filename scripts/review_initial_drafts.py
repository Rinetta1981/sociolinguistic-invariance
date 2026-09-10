import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sociolinguistic_invariance.audit import (
    create_review_record,
    review_record_to_dict,
)
from sociolinguistic_invariance.authoring import semantic_family_to_dict
from sociolinguistic_invariance.core import SemanticFamily, ValidationStatus
from sociolinguistic_invariance.data_io import (
    load_semantic_family,
    validate_semantic_family_record,
)
from sociolinguistic_invariance.review import ReviewChecklist, mark_reviewed

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DISCOVERY_DIR = PROJECT_ROOT / "data" / "discovery"
REVIEW_DIR = PROJECT_ROOT / "data" / "metadata" / "reviews"

REVIEWER_ID = "Irene Theodoropoulou"

FAMILY_IDS = (
    "FP_0001",
    "EU_0001",
    "BR_0001",
)

REVIEW_NOTES = {
    "FP_0001": (
        "Approved on all six review criteria after revising the standard and "
        "informal wording for clearer register differentiation while preserving "
        "the false premise."
    ),
    "EU_0001": (
        "Approved on all six review criteria after revising the informal wording "
        "for sociolinguistic naturalness while preserving the probability task."
    ),
    "BR_0001": (
        "Approved on all six review criteria after aligning the referential "
        "wording 'μια λίστα αγορών' across standard and informal conditions."
    ),
}


def build_checklist(family_id: str) -> ReviewChecklist:
    """Return the manually approved checklist for one semantic family."""

    return ReviewChecklist(
        reviewer_id=REVIEWER_ID,
        semantic_equivalence=True,
        sociolinguistic_naturalness=True,
        factual_content_preserved=True,
        expected_behavior_clear=True,
        no_prohibited_confounds=True,
        greeklish_verified=True,
        notes=REVIEW_NOTES[family_id],
    )


def load_draft_family(family_id: str) -> SemanticFamily:
    """Load one family and require it to still be in draft status."""

    path = DISCOVERY_DIR / f"{family_id}.json"
    family = load_semantic_family(path)

    if family.validation_status is not ValidationStatus.DRAFT:
        raise ValueError(
            f"{family_id} must be draft before review; "
            f"found {family.validation_status.value!r}."
        )

    return family


def write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write UTF-8 JSON to disk."""

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
    """Record the approved human review for the initial discovery families."""

    REVIEW_DIR.mkdir(parents=True, exist_ok=True)

    families = {
        family_id: load_draft_family(family_id)
        for family_id in FAMILY_IDS
    }

    for family_id in FAMILY_IDS:
        review_path = REVIEW_DIR / f"{family_id}.review.json"

        if review_path.exists():
            raise FileExistsError(
                "Review record already exists and will not be overwritten: "
                f"{review_path}"
            )

    reviewed_at = datetime.now(UTC)

    for family_id, family in families.items():
        checklist = build_checklist(family_id)

        reviewed_family = mark_reviewed(
            family,
            checklist,
        )

        family_payload = semantic_family_to_dict(reviewed_family)
        validate_semantic_family_record(family_payload)

        review_record = create_review_record(
            reviewed_family,
            checklist,
            reviewed_at=reviewed_at,
        )
        review_payload = review_record_to_dict(review_record)

        family_path = DISCOVERY_DIR / f"{family_id}.json"
        review_path = REVIEW_DIR / f"{family_id}.review.json"

        write_json(
            family_path,
            family_payload,
        )
        write_json(
            review_path,
            review_payload,
        )

        print(f"Reviewed {family_id}")
        print(f"  family -> {family_path.relative_to(PROJECT_ROOT)}")
        print(f"  audit  -> {review_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()