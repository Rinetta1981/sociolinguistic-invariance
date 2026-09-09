import json
from pathlib import Path
from typing import Any

from sociolinguistic_invariance.core import SemanticFamily, ValidationStatus


def semantic_family_to_dict(family: SemanticFamily) -> dict[str, Any]:
    """Convert a semantic family into its canonical JSON representation."""

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
        "validation_status": family.validation_status.value,
    }


def save_draft_semantic_family(
    family: SemanticFamily,
    path: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Save one draft semantic family as UTF-8 JSON."""

    if family.validation_status is not ValidationStatus.DRAFT:
        raise ValueError("authoring workflow only saves draft families")

    output_path = Path(path)

    if output_path.exists() and not overwrite:
        raise FileExistsError(
            f"refusing to overwrite existing semantic family: {output_path}"
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_path.write_text(
        json.dumps(
            semantic_family_to_dict(family),
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    return output_path