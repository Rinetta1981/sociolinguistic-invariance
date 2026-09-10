import hashlib
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from sociolinguistic_invariance.core import (
    SemanticFamily,
    TaskType,
    ValidationStatus,
    VariationCondition,
)
from sociolinguistic_invariance.data_io import semantic_family_from_dict
from sociolinguistic_invariance.evaluation import (
    EvaluationRequest,
    build_evaluation_request,
)

EVALUATION_CONDITIONS: Final = (
    VariationCondition.STANDARD,
    VariationCondition.FORMAL,
    VariationCondition.INFORMAL,
    VariationCondition.GREEKLISH,
)


@dataclass(frozen=True, slots=True)
class FrozenArtifactManifest:
    """Manifest fields needed to verify one frozen benchmark artifact."""

    artifact_id: str
    export_file: str
    export_sha256: str
    family_count: int
    freeze_protocol_version: str
    review_protocol_version: str


@dataclass(frozen=True, slots=True)
class EvaluationPlan:
    """Provider-neutral dry-run plan for one frozen benchmark artifact."""

    run_id: str
    artifact_id: str
    artifact_path: str
    artifact_sha256: str
    randomized: bool
    order_seed: int | None
    requests: tuple[EvaluationRequest, ...]

    @property
    def request_count(self) -> int:
        """Return the number of planned model requests."""

        return len(self.requests)


def _require_nonblank_manifest_string(
    record: dict[str, object],
    field_name: str,
) -> str:
    """Read and validate one required string from a manifest."""

    value = record.get(field_name)

    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"Manifest field {field_name!r} must be a non-blank string."
        )

    return value


def _require_manifest_family_count(
    record: dict[str, object],
) -> int:
    """Read and validate the manifest family count."""

    value = record.get("family_count")

    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(
            "Manifest field 'family_count' must be an integer."
        )

    if value <= 0:
        raise ValueError(
            "Manifest field 'family_count' must be positive."
        )

    return value


def _validate_sha256(
    value: str,
    *,
    field_name: str,
) -> None:
    """Require a lowercase SHA-256 hexadecimal digest."""

    if len(value) != 64:
        raise ValueError(
            f"{field_name} must contain exactly 64 hexadecimal characters."
        )

    if any(
        character not in "0123456789abcdef"
        for character in value
    ):
        raise ValueError(
            f"{field_name} must be lowercase hexadecimal."
        )


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of exact file bytes."""

    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for block in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(block)

    return digest.hexdigest()


def load_frozen_manifest(
    manifest_path: Path,
) -> FrozenArtifactManifest:
    """Load and minimally validate a frozen benchmark manifest."""

    with manifest_path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        raw_record = json.load(handle)

    if not isinstance(raw_record, dict):
        raise ValueError(
            "Frozen artifact manifest must contain a JSON object."
        )

    record: dict[str, object] = raw_record

    artifact_id = _require_nonblank_manifest_string(
        record,
        "artifact_id",
    )
    export_file = _require_nonblank_manifest_string(
        record,
        "export_file",
    )
    export_sha256 = _require_nonblank_manifest_string(
        record,
        "export_sha256",
    )
    freeze_protocol_version = _require_nonblank_manifest_string(
        record,
        "freeze_protocol_version",
    )
    review_protocol_version = _require_nonblank_manifest_string(
        record,
        "review_protocol_version",
    )
    family_count = _require_manifest_family_count(
        record
    )

    _validate_sha256(
        export_sha256,
        field_name="export_sha256",
    )

    return FrozenArtifactManifest(
        artifact_id=artifact_id,
        export_file=export_file,
        export_sha256=export_sha256,
        family_count=family_count,
        freeze_protocol_version=freeze_protocol_version,
        review_protocol_version=review_protocol_version,
    )


def verify_frozen_artifact(
    *,
    artifact_path: Path,
    manifest_path: Path,
) -> FrozenArtifactManifest:
    """Verify exact frozen artifact bytes against the manifest."""

    manifest = load_frozen_manifest(
        manifest_path
    )

    actual_sha256 = sha256_file(
        artifact_path
    )

    if actual_sha256 != manifest.export_sha256:
        raise ValueError(
            "Frozen artifact SHA-256 mismatch. "
            f"Expected {manifest.export_sha256}; "
            f"found {actual_sha256}."
        )

    return manifest


def load_frozen_families(
    artifact_path: Path,
) -> tuple[SemanticFamily, ...]:
    """Load validated frozen semantic families from JSONL."""

    families: list[SemanticFamily] = []
    seen_family_ids: set[str] = set()

    with artifact_path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        for line_number, raw_line in enumerate(
            handle,
            start=1,
        ):
            if not raw_line.strip():
                raise ValueError(
                    "Frozen artifact contains a blank line at "
                    f"line {line_number}."
                )

            try:
                raw_record = json.loads(
                    raw_line
                )
            except json.JSONDecodeError as error:
                raise ValueError(
                    "Invalid JSON in frozen artifact at "
                    f"line {line_number}."
                ) from error

            if not isinstance(raw_record, dict):
                raise ValueError(
                    "Frozen artifact line "
                    f"{line_number} must contain a JSON object."
                )

            record: dict[str, object] = raw_record

            family = semantic_family_from_dict(
                record
            )

            if (
                family.validation_status
                is not ValidationStatus.FROZEN
            ):
                raise ValueError(
                    f"Family {family.family_id!r} is not frozen."
                )

            if family.family_id in seen_family_ids:
                raise ValueError(
                    "Duplicate semantic family ID in frozen artifact: "
                    f"{family.family_id!r}."
                )

            seen_family_ids.add(
                family.family_id
            )
            families.append(
                family
            )

    if not families:
        raise ValueError(
            "Frozen artifact contains no semantic families."
        )

    return tuple(families)


def _family_prompt_items(
    families: tuple[SemanticFamily, ...],
) -> list[
    tuple[
        str,
        TaskType,
        VariationCondition,
        str,
    ]
]:
    """Expand semantic families into condition-level prompt items."""

    items: list[
        tuple[
            str,
            TaskType,
            VariationCondition,
            str,
        ]
    ] = []

    for family in families:
        variants_by_condition = {
            variant.condition: variant.text
            for variant in family.variants
        }

        missing = [
            condition.value
            for condition in EVALUATION_CONDITIONS
            if condition not in variants_by_condition
        ]

        if missing:
            raise ValueError(
                f"Family {family.family_id!r} is missing conditions: "
                + ", ".join(missing)
            )

        for condition in EVALUATION_CONDITIONS:
            items.append(
                (
                    family.family_id,
                    family.task_type,
                    condition,
                    variants_by_condition[condition],
                )
            )

    return items


def build_evaluation_plan(
    *,
    run_id: str,
    artifact_path: Path,
    manifest_path: Path,
    randomized: bool,
    order_seed: int | None,
) -> EvaluationPlan:
    """Verify a frozen artifact and construct its request plan."""

    if not run_id.strip():
        raise ValueError(
            "run_id must be non-blank."
        )

    if randomized and order_seed is None:
        raise ValueError(
            "Randomized evaluation requires an order_seed."
        )

    manifest = verify_frozen_artifact(
        artifact_path=artifact_path,
        manifest_path=manifest_path,
    )

    families = load_frozen_families(
        artifact_path
    )

    if len(families) != manifest.family_count:
        raise ValueError(
            "Frozen family count does not match manifest. "
            f"Expected {manifest.family_count}; "
            f"found {len(families)}."
        )

    items = _family_prompt_items(
        families
    )

    if randomized:
        generator = random.Random(
            order_seed
        )
        generator.shuffle(
            items
        )

    requests: list[EvaluationRequest] = []

    for order_index, (
        family_id,
        task_type,
        condition,
        prompt_text,
    ) in enumerate(items):
        requests.append(
            build_evaluation_request(
                run_id=run_id,
                family_id=family_id,
                task_type=task_type,
                condition=condition,
                prompt_text=prompt_text,
                order_index=order_index,
            )
        )

    return EvaluationPlan(
        run_id=run_id,
        artifact_id=manifest.artifact_id,
        artifact_path=artifact_path.as_posix(),
        artifact_sha256=manifest.export_sha256,
        randomized=randomized,
        order_seed=order_seed,
        requests=tuple(requests),
    )


def evaluation_plan_to_dict(
    plan: EvaluationPlan,
) -> dict[str, object]:
    """Serialize a dry-run evaluation plan without model responses."""

    return {
        "run_id": plan.run_id,
        "artifact_id": plan.artifact_id,
        "artifact_path": plan.artifact_path,
        "artifact_sha256": plan.artifact_sha256,
        "randomized": plan.randomized,
        "order_seed": plan.order_seed,
        "request_count": plan.request_count,
        "requests": [
            {
                "order_index": request.order_index,
                "request_id": request.request_id,
                "family_id": request.family_id,
                "task_type": request.task_type.value,
                "condition": request.condition.value,
                "prompt_text": request.prompt_text,
                "prompt_sha256": request.prompt_sha256,
            }
            for request in plan.requests
        ],
    }