import hashlib
import json
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Final, cast

ANNOTATION_SOURCE_ARTIFACT_TYPE: Final = (
    "single_response_annotation_source"
)

ANNOTATION_SOURCE_FORMAT_VERSION: Final = (
    "single-response-annotation-source-v0.1"
)

_SAFE_COMPONENT_PATTERN: Final = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9._-]*$"
)


@dataclass(
    frozen=True,
    slots=True,
)
class PreparedAnnotationSource:
    """One single-response artifact ready for human annotation."""

    run_id: str
    request_id: str
    family_id: str
    condition: str
    filename: str
    payload: dict[str, object]


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


def _require_list(
    value: object,
    *,
    field_name: str,
) -> list[object]:
    """Require a JSON array."""

    if not isinstance(
        value,
        list,
    ):
        raise ValueError(
            f"{field_name} must be a JSON array."
        )

    return cast(
        list[object],
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
        not isinstance(
            value,
            str,
        )
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


def _require_int(
    mapping: dict[str, object],
    key: str,
    *,
    context: str,
) -> int:
    """Return one required integer."""

    value = mapping.get(
        key
    )

    if (
        not isinstance(
            value,
            int,
        )
        or isinstance(
            value,
            bool,
        )
    ):
        raise ValueError(
            f"{context}.{key} must be an int."
        )

    return value


def _safe_component(
    value: str,
    *,
    field_name: str,
) -> str:
    """Validate one filename-safe identifier."""

    if (
        value in {
            ".",
            "..",
        }
        or _SAFE_COMPONENT_PATTERN.fullmatch(
            value
        )
        is None
    ):
        raise ValueError(
            f"{field_name} is not safe for use "
            f"in a filename: {value!r}."
        )

    return value


def sha256_file(
    path: Path,
) -> str:
    """Return the SHA-256 digest of one file."""

    digest = hashlib.sha256()

    with path.open(
        "rb"
    ) as handle:
        while True:
            chunk = handle.read(
                1024 * 1024
            )

            if not chunk:
                break

            digest.update(
                chunk
            )

    return digest.hexdigest()


def repository_relative_label(
    *,
    path: Path,
    repo_root: Path,
) -> str:
    """Return a stable repository-relative label when possible."""

    resolved_path = path.resolve()
    resolved_root = repo_root.resolve()

    try:
        return (
            resolved_path
            .relative_to(
                resolved_root
            )
            .as_posix()
        )
    except ValueError:
        return str(
            resolved_path
        )


def load_raw_results_artifact(
    path: Path,
) -> dict[str, object]:
    """Load one raw batch-results JSON artifact."""

    if not path.exists():
        raise FileNotFoundError(
            "Raw results artifact does not exist: "
            f"{path}"
        )

    raw_object: object = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    return _require_mapping(
        raw_object,
        field_name="artifact",
    )


def _validate_request_result_binding(
    *,
    request: dict[str, object],
    result: dict[str, object],
) -> None:
    """Require result metadata to match its evaluation request."""

    request_id = _require_string(
        request,
        "request_id",
        context="request",
    )

    result_request_id = _require_string(
        result,
        "request_id",
        context="result",
    )

    if request_id != result_request_id:
        raise ValueError(
            "Request/result request_id mismatch: "
            f"{request_id!r} != "
            f"{result_request_id!r}."
        )

    for key in (
        "run_id",
        "family_id",
        "task_type",
        "condition",
        "prompt_sha256",
    ):
        request_value = _require_string(
            request,
            key,
            context="request",
        )

        result_value = _require_string(
            result,
            key,
            context="result",
        )

        if request_value != result_value:
            raise ValueError(
                "Request/result binding mismatch "
                f"for {key}: "
                f"{request_value!r} != "
                f"{result_value!r}."
            )

    status = _require_string(
        result,
        "status",
        context="result",
    )

    if status != "SUCCESS":
        raise ValueError(
            "Only successful responses may be "
            "prepared for human annotation. "
            f"Observed status: {status!r}."
        )

    _require_string(
        result,
        "response_text",
        context="result",
    )


def _index_results(
    results: list[object],
) -> dict[str, dict[str, object]]:
    """Index serialized results by request ID."""

    indexed: dict[
        str,
        dict[str, object],
    ] = {}

    for index, item in enumerate(
        results
    ):
        result = _require_mapping(
            item,
            field_name=(
                f"artifact.results[{index}]"
            ),
        )

        request_id = _require_string(
            result,
            "request_id",
            context=(
                f"artifact.results[{index}]"
            ),
        )

        if request_id in indexed:
            raise ValueError(
                "Duplicate result request_id: "
                f"{request_id!r}."
            )

        indexed[
            request_id
        ] = result

    return indexed


def annotation_source_filename(
    *,
    run_id: str,
    family_id: str,
    condition: str,
) -> str:
    """Return a deterministic safe annotation-source filename."""

    safe_run_id = _safe_component(
        run_id,
        field_name="run_id",
    )

    safe_family_id = _safe_component(
        family_id,
        field_name="family_id",
    )

    safe_condition = _safe_component(
        condition,
        field_name="condition",
    )

    return (
        f"{safe_run_id}_"
        f"{safe_family_id}_"
        f"{safe_condition}.json"
    )


def prepare_annotation_sources(
    *,
    batch: dict[str, object],
    source_artifact: str,
    source_artifact_sha256: str,
) -> tuple[
    PreparedAnnotationSource,
    ...,
]:
    """Split one complete raw-results artifact into annotation sources."""

    artifact_type = _require_string(
        batch,
        "artifact_type",
        context="artifact",
    )

    run_id = _require_string(
        batch,
        "run_id",
        context="artifact",
    )

    artifact_id = _require_string(
        batch,
        "artifact_id",
        context="artifact",
    )

    artifact_sha256 = _require_string(
        batch,
        "artifact_sha256",
        context="artifact",
    )

    benchmark_claim_eligible = (
        _require_bool(
            batch,
            "benchmark_claim_eligible",
            context="artifact",
        )
    )

    result_count = _require_int(
        batch,
        "result_count",
        context="artifact",
    )

    plan = _require_mapping(
        batch.get(
            "plan"
        ),
        field_name="artifact.plan",
    )

    requests = _require_list(
        plan.get(
            "requests"
        ),
        field_name=(
            "artifact.plan.requests"
        ),
    )

    results = _require_list(
        batch.get(
            "results"
        ),
        field_name="artifact.results",
    )

    if result_count != len(
        results
    ):
        raise ValueError(
            "artifact.result_count does not "
            "match len(artifact.results)."
        )

    if len(
        requests
    ) != len(
        results
    ):
        raise ValueError(
            "The number of planned requests does "
            "not match the number of results."
        )

    result_by_request = _index_results(
        results
    )

    prepared: list[
        PreparedAnnotationSource
    ] = []

    seen_request_ids: set[str] = set()

    git_provenance = _require_mapping(
        batch.get(
            "git_provenance"
        ),
        field_name=(
            "artifact.git_provenance"
        ),
    )

    model_configuration = _require_mapping(
        batch.get(
            "model_configuration"
        ),
        field_name=(
            "artifact.model_configuration"
        ),
    )

    research_phase = _require_string(
        batch,
        "research_phase",
        context="artifact",
    )

    for index, item in enumerate(
        requests
    ):
        request = _require_mapping(
            item,
            field_name=(
                "artifact.plan.requests"
                f"[{index}]"
            ),
        )

        request_id = _require_string(
            request,
            "request_id",
            context=(
                "artifact.plan.requests"
                f"[{index}]"
            ),
        )

        if request_id in seen_request_ids:
            raise ValueError(
                "Duplicate planned request_id: "
                f"{request_id!r}."
            )

        seen_request_ids.add(
            request_id
        )

        try:
            result = result_by_request[
                request_id
            ]
        except KeyError as error:
            raise ValueError(
                "No evaluation result exists for "
                f"request_id {request_id!r}."
            ) from error

        _validate_request_result_binding(
            request=request,
            result=result,
        )

        request_run_id = _require_string(
            request,
            "run_id",
            context="request",
        )

        if request_run_id != run_id:
            raise ValueError(
                "Batch/request run_id mismatch: "
                f"{run_id!r} != "
                f"{request_run_id!r}."
            )

        family_id = _require_string(
            request,
            "family_id",
            context="request",
        )

        condition = _require_string(
            request,
            "condition",
            context="request",
        )

        filename = (
            annotation_source_filename(
                run_id=run_id,
                family_id=family_id,
                condition=condition,
            )
        )

        payload: dict[
            str,
            object,
        ] = {
            "artifact_type": (
                ANNOTATION_SOURCE_ARTIFACT_TYPE
            ),
            "annotation_source_format_version": (
                ANNOTATION_SOURCE_FORMAT_VERSION
            ),
            "benchmark_claim_eligible": (
                benchmark_claim_eligible
            ),
            "request": dict(
                request
            ),
            "result": dict(
                result
            ),
            "source": {
                "artifact": source_artifact,
                "artifact_sha256": (
                    source_artifact_sha256
                ),
                "artifact_type": artifact_type,
                "run_id": run_id,
                "benchmark_artifact_id": (
                    artifact_id
                ),
                "benchmark_artifact_sha256": (
                    artifact_sha256
                ),
                "research_phase": (
                    research_phase
                ),
                "git_provenance": dict(
                    git_provenance
                ),
                "model_configuration": dict(
                    model_configuration
                ),
            },
        }

        prepared.append(
            PreparedAnnotationSource(
                run_id=run_id,
                request_id=request_id,
                family_id=family_id,
                condition=condition,
                filename=filename,
                payload=payload,
            )
        )

    if set(
        result_by_request
    ) != seen_request_ids:
        unexpected = sorted(
            set(
                result_by_request
            )
            - seen_request_ids
        )

        raise ValueError(
            "Results contain request IDs that are "
            "not present in the plan: "
            f"{unexpected!r}."
        )

    return tuple(
        prepared
    )


def _write_json_atomic(
    *,
    path: Path,
    payload: dict[str, object],
    overwrite: bool,
) -> None:
    """Write one JSON artifact atomically."""

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if (
        path.exists()
        and not overwrite
    ):
        raise FileExistsError(
            "Refusing to overwrite existing "
            f"annotation source: {path}"
        )

    temporary_path: Path | None = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_path = Path(
                handle.name
            )

            json.dump(
                payload,
                handle,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )

            handle.write(
                "\n"
            )

            handle.flush()

            os.fsync(
                handle.fileno()
            )

        if (
            path.exists()
            and not overwrite
        ):
            raise FileExistsError(
                "Refusing to overwrite existing "
                f"annotation source: {path}"
            )

        os.replace(
            temporary_path,
            path,
        )

        temporary_path = None

    finally:
        if (
            temporary_path is not None
            and temporary_path.exists()
        ):
            temporary_path.unlink()


def write_annotation_sources_atomic(
    *,
    output_dir: Path,
    sources: tuple[
        PreparedAnnotationSource,
        ...,
    ],
    overwrite: bool = False,
) -> tuple[
    Path,
    ...,
]:
    """Write prepared annotation sources without silent overwrite."""

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    paths = tuple(
        output_dir
        / source.filename
        for source in sources
    )

    if len(
        set(
            paths
        )
    ) != len(
        paths
    ):
        raise ValueError(
            "Prepared annotation sources contain "
            "duplicate output paths."
        )

    if not overwrite:
        existing = [
            path
            for path in paths
            if path.exists()
        ]

        if existing:
            raise FileExistsError(
                "Refusing to overwrite existing "
                "annotation-source files: "
                + ", ".join(
                    str(
                        path
                    )
                    for path in existing
                )
            )

    written: list[
        Path
    ] = []

    for source, path in zip(
        sources,
        paths,
        strict=True,
    ):
        _write_json_atomic(
            path=path,
            payload=source.payload,
            overwrite=overwrite,
        )

        written.append(
            path
        )

    return tuple(
        written
    )