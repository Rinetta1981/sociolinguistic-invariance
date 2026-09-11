import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from sociolinguistic_invariance.annotation import (
    AnnotationDecision,
    CriterionAnnotation,
)
from sociolinguistic_invariance.annotation_workflow import (
    AnnotationSource,
    annotation_output_path,
    create_scored_response_annotation,
    human_scored_response_artifact_to_dict,
    write_human_scored_response_artifact_atomic,
)
from sociolinguistic_invariance.core import (
    TaskType,
    VariationCondition,
)
from sociolinguistic_invariance.provenance import (
    capture_git_provenance,
    require_clean_git_worktree,
)
from sociolinguistic_invariance.rubric import (
    CriterionDefinition,
    get_task_rubric,
)


def _require_mapping(
    value: object,
    *,
    field_name: str,
) -> dict[str, object]:
    """Require a JSON object."""

    if not isinstance(
        value,
        dict,
    ):
        raise ValueError(
            f"{field_name} must be a JSON object."
        )

    return cast(
        dict[str, object],
        value,
    )


def _require_string(
    mapping: dict[str, object],
    key: str,
    *,
    context: str,
) -> str:
    """Return one required non-blank string."""

    value = mapping.get(
        key
    )

    if (
        not isinstance(value, str)
        or not value.strip()
    ):
        raise ValueError(
            f"{context}.{key} must be "
            "a non-blank string."
        )

    return value


def _require_bool(
    mapping: dict[str, object],
    key: str,
    *,
    context: str,
) -> bool:
    """Return one required Boolean."""

    value = mapping.get(
        key
    )

    if not isinstance(
        value,
        bool,
    ):
        raise ValueError(
            f"{context}.{key} must be a bool."
        )

    return value


def _source_artifact_label(
    *,
    source_path: Path,
    repo_root: Path,
) -> str:
    """Return a stable repository-relative path when possible."""

    try:
        return (
            source_path
            .relative_to(
                repo_root
            )
            .as_posix()
        )
    except ValueError:
        return str(
            source_path
        )


def load_annotation_source(
    *,
    source_path: Path,
    repo_root: Path,
) -> AnnotationSource:
    """Load one successful single-response evaluation artifact."""

    if not source_path.exists():
        raise FileNotFoundError(
            "Source artifact does not exist: "
            f"{source_path}"
        )

    raw_object: object = json.loads(
        source_path.read_text(
            encoding="utf-8"
        )
    )

    raw = _require_mapping(
        raw_object,
        field_name="artifact",
    )

    request = _require_mapping(
        raw.get("request"),
        field_name="artifact.request",
    )

    result = _require_mapping(
        raw.get("result"),
        field_name="artifact.result",
    )

    status = _require_string(
        result,
        "status",
        context="artifact.result",
    )

    if status != "SUCCESS":
        raise ValueError(
            "Only a successful model response "
            "can be annotated. "
            f"Observed status: {status!r}."
        )

    response_text = _require_string(
        result,
        "response_text",
        context="artifact.result",
    )

    artifact_type = _require_string(
        raw,
        "artifact_type",
        context="artifact",
    )

    benchmark_claim_eligible = (
        _require_bool(
            raw,
            "benchmark_claim_eligible",
            context="artifact",
        )
    )

    run_id = _require_string(
        request,
        "run_id",
        context="artifact.request",
    )

    request_id = _require_string(
        request,
        "request_id",
        context="artifact.request",
    )

    family_id = _require_string(
        request,
        "family_id",
        context="artifact.request",
    )

    task_type_value = _require_string(
        request,
        "task_type",
        context="artifact.request",
    )

    condition_value = _require_string(
        request,
        "condition",
        context="artifact.request",
    )

    try:
        task_type = TaskType(
            task_type_value
        )
    except ValueError as error:
        raise ValueError(
            "artifact.request.task_type "
            f"is unsupported: {task_type_value!r}."
        ) from error

    try:
        condition = VariationCondition(
            condition_value
        )
    except ValueError as error:
        raise ValueError(
            "artifact.request.condition "
            f"is unsupported: {condition_value!r}."
        ) from error

    return AnnotationSource(
        source_artifact=(
            _source_artifact_label(
                source_path=source_path,
                repo_root=repo_root,
            )
        ),
        source_artifact_type=artifact_type,
        source_benchmark_claim_eligible=(
            benchmark_claim_eligible
        ),
        run_id=run_id,
        request_id=request_id,
        family_id=family_id,
        task_type=task_type,
        condition=condition,
        response_text=response_text,
    )


def _print_criterion(
    criterion: CriterionDefinition,
) -> None:
    """Display one annotation criterion."""

    print()
    print(
        "=" * 72
    )
    print(
        f"Criterion {criterion.criterion_id}"
    )
    print(
        "=" * 72
    )
    print(
        criterion.question
    )
    print()
    print(
        "YES:"
    )
    print(
        criterion.yes_definition
    )
    print()
    print(
        "NO:"
    )
    print(
        criterion.no_definition
    )
    print()
    print(
        "UNCLEAR:"
    )
    print(
        criterion.unclear_definition
    )


def _prompt_decision(
    criterion_id: str,
) -> AnnotationDecision:
    """Prompt until a valid annotation decision is entered."""

    while True:
        raw = input(
            f"{criterion_id} decision "
            "[YES/NO/UNCLEAR]: "
        )

        normalized = (
            raw.strip().upper()
        )

        try:
            return AnnotationDecision(
                normalized
            )
        except ValueError:
            print(
                "Please enter exactly "
                "YES, NO, or UNCLEAR."
            )


def _prompt_optional_text(
    prompt: str,
) -> str | None:
    """Return stripped optional input."""

    value = input(
        prompt
    ).strip()

    if not value:
        return None

    return value


def _prompt_rationale(
    *,
    criterion_id: str,
    decision: AnnotationDecision,
) -> str | None:
    """Collect rationale, requiring it for UNCLEAR."""

    while True:
        rationale = _prompt_optional_text(
            f"{criterion_id} rationale "
            "(Enter to leave blank): "
        )

        if (
            decision
            is not AnnotationDecision.UNCLEAR
            or rationale is not None
        ):
            return rationale

        print(
            "UNCLEAR requires a rationale. "
            "Please explain why the judgment "
            "cannot be resolved."
        )


def _annotate_criterion(
    criterion: CriterionDefinition,
) -> CriterionAnnotation:
    """Collect one human criterion annotation."""

    _print_criterion(
        criterion
    )

    decision = _prompt_decision(
        criterion.criterion_id
    )

    rationale = _prompt_rationale(
        criterion_id=(
            criterion.criterion_id
        ),
        decision=decision,
    )

    evidence = _prompt_optional_text(
        f"{criterion.criterion_id} evidence "
        "(optional exact response excerpt; "
        "Enter to leave blank): "
    )

    return CriterionAnnotation(
        criterion_id=(
            criterion.criterion_id
        ),
        decision=decision,
        rationale=rationale,
        evidence=evidence,
    )


def _build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""

    parser = argparse.ArgumentParser(
        description=(
            "Human-annotate one successful "
            "single-response evaluation artifact "
            "and derive its deterministic score."
        )
    )

    parser.add_argument(
        "source",
        type=Path,
        help=(
            "Path to the source evaluation "
            "JSON artifact."
        ),
    )

    parser.add_argument(
        "--annotator-id",
        required=True,
        help=(
            "Stable non-blank identifier for "
            "the human annotator."
        ),
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(
            "results/annotations"
        ),
        help=(
            "Directory for generated annotation "
            "artifacts."
        ),
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
        help=(
            "Explicitly allow replacement of an "
            "existing annotation artifact."
        ),
    )

    return parser


def main() -> int:
    """Run the interactive annotation workflow."""

    parser = _build_parser()

    args = parser.parse_args()

    source_argument = cast(
        Path,
        args.source,
    )

    annotator_id = cast(
        str,
        args.annotator_id,
    ).strip()

    output_directory = cast(
        Path,
        args.output_dir,
    )

    overwrite = cast(
        bool,
        args.overwrite,
    )

    if not annotator_id:
        parser.error(
            "--annotator-id must be non-blank."
        )

    repo_root = Path(
        "."
    ).resolve()

    source_path = (
        source_argument.resolve()
    )

    provenance = capture_git_provenance(
        repo_root
    )

    require_clean_git_worktree(
        provenance
    )

    source = load_annotation_source(
        source_path=source_path,
        repo_root=repo_root,
    )

    rubric = get_task_rubric(
        source.task_type
    )

    print()
    print(
        "=" * 72
    )
    print(
        "HUMAN RESPONSE ANNOTATION"
    )
    print(
        "=" * 72
    )
    print(
        f"Source: {source.source_artifact}"
    )
    print(
        f"Run: {source.run_id}"
    )
    print(
        f"Request: {source.request_id}"
    )
    print(
        f"Family: {source.family_id}"
    )
    print(
        f"Task: {source.task_type.value}"
    )
    print(
        f"Condition: {source.condition.value}"
    )
    print(
        f"Rubric: {rubric.rubric_version}"
    )
    print(
        f"Annotator: {annotator_id}"
    )

    print()
    print(
        "=" * 72
    )
    print(
        "EXACT MODEL RESPONSE"
    )
    print(
        "=" * 72
    )
    print(
        source.response_text
    )

    criteria = tuple(
        _annotate_criterion(
            criterion
        )
        for criterion in rubric.criteria
    )

    scored = (
        create_scored_response_annotation(
            source=source,
            annotator_id=annotator_id,
            criteria=criteria,
            created_at=datetime.now(
                UTC
            ),
        )
    )

    payload = (
        human_scored_response_artifact_to_dict(
            source=source,
            scored=scored,
            git_provenance=provenance,
        )
    )

    output_path = annotation_output_path(
        output_directory=(
            output_directory.resolve()
        ),
        annotation=scored.annotation,
    )

    write_human_scored_response_artifact_atomic(
        path=output_path,
        payload=payload,
        overwrite=overwrite,
    )

    print()
    print(
        "=" * 72
    )
    print(
        "ANNOTATION COMPLETE"
    )
    print(
        "=" * 72
    )
    print(
        f"Outcome: {scored.score.outcome.value}"
    )
    print(
        "Response SHA-256: "
        f"{scored.annotation.response_sha256}"
    )
    print(
        "Source benchmark claim eligible: "
        f"{source.source_benchmark_claim_eligible}"
    )
    print(
        "Output: "
        f"{output_path}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )