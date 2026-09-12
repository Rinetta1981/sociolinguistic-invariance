import json
from pathlib import Path

import pytest

from sociolinguistic_invariance.annotation_source_export import (
    ANNOTATION_SOURCE_ARTIFACT_TYPE,
    ANNOTATION_SOURCE_FORMAT_VERSION,
    PreparedAnnotationSource,
    annotation_source_filename,
    prepare_annotation_sources,
    sha256_file,
    write_annotation_sources_atomic,
)


def _request(
    *,
    request_id: str = "req-001",
    family_id: str = "FP_0001",
    task_type: str = "false_premise_correction",
    condition: str = "standard",
    prompt_sha256: str = "a" * 64,
) -> dict[str, object]:
    """Return one request using the real plan-request schema."""

    return {
        "request_id": request_id,
        "family_id": family_id,
        "task_type": task_type,
        "condition": condition,
        "prompt_text": (
            "Η Μαδρίτη είναι η πρωτεύουσα "
            "της Πορτογαλίας. Γιατί;"
        ),
        "prompt_sha256": prompt_sha256,
        "order_index": 0,
    }


def _result(
    *,
    request_id: str = "req-001",
    run_id: str = "run-001",
    family_id: str = "FP_0001",
    task_type: str = "false_premise_correction",
    condition: str = "standard",
    prompt_sha256: str = "a" * 64,
    status: str = "SUCCESS",
    response_text: str = (
        "Η Μαδρίτη δεν είναι η πρωτεύουσα "
        "της Πορτογαλίας."
    ),
) -> dict[str, object]:
    """Return one serialized evaluation result."""

    return {
        "run_id": run_id,
        "request_id": request_id,
        "family_id": family_id,
        "task_type": task_type,
        "condition": condition,
        "provider": "ollama",
        "requested_model": "gemma3:4b",
        "returned_model": "gemma3:4b",
        "prompt_sha256": prompt_sha256,
        "status": status,
        "response_text": response_text,
        "request_started_at": (
            "2026-09-12T00:00:00Z"
        ),
        "response_finished_at": (
            "2026-09-12T00:00:01Z"
        ),
        "latency_seconds": 1.0,
        "retry_count": 0,
        "attempts": [],
        "provider_request_id": None,
        "finish_reason": "stop",
        "usage": {
            "input_tokens": 10,
            "output_tokens": 20,
            "total_tokens": 30,
        },
        "error_type": None,
        "error_message": None,
        "evaluation_protocol_version": (
            "evaluation-protocol-v0.1"
        ),
    }


def _batch(
    *,
    requests: list[
        dict[str, object]
    ]
    | None = None,
    results: list[
        dict[str, object]
    ]
    | None = None,
    batch_run_id: str = "run-001",
    plan_run_id: str = "run-001",
    benchmark_claim_eligible: bool = False,
    result_count: int | None = None,
    plan_request_count: int | None = None,
) -> dict[str, object]:
    """Return one realistic raw-results artifact."""

    request_records = (
        requests
        if requests is not None
        else [
            _request()
        ]
    )

    result_records = (
        results
        if results is not None
        else [
            _result(
                run_id=batch_run_id
            )
        ]
    )

    observed_result_count = (
        len(result_records)
        if result_count is None
        else result_count
    )

    observed_request_count = (
        len(request_records)
        if plan_request_count is None
        else plan_request_count
    )

    return {
        "artifact_type": (
            "raw_evaluation_results"
        ),
        "raw_results_format_version": (
            "raw-results-v0.1"
        ),
        "run_id": batch_run_id,
        "artifact_id": "pilot_v0.1",
        "artifact_sha256": "b" * 64,
        "git_provenance": {
            "available": True,
            "commit": "abc123",
            "worktree_clean": True,
            "status_entry_count": 0,
            "status_sha256": None,
        },
        "model_configuration": {
            "provider": "ollama",
            "requested_model": "gemma3:4b",
            "temperature": 0.0,
            "top_p": None,
            "max_output_tokens": 512,
            "seed": 20260911,
            "system_instruction": (
                "Answer the user's request "
                "directly and accurately."
            ),
            "sdk_version": None,
        },
        "plan": {
            "run_id": plan_run_id,
            "artifact_id": "pilot_v0.1",
            "artifact_path": (
                "data/frozen/pilot_v0.1.jsonl"
            ),
            "artifact_sha256": "b" * 64,
            "randomized": True,
            "order_seed": 20260910,
            "request_count": (
                observed_request_count
            ),
            "requests": request_records,
        },
        "result_count": observed_result_count,
        "status_counts": {
            "SUCCESS": len(
                result_records
            ),
            "PROVIDER_ERROR": 0,
            "TIMEOUT": 0,
            "RATE_LIMITED": 0,
            "INVALID_RESPONSE": 0,
            "SKIPPED": 0,
        },
        "results": result_records,
        "research_phase": "discovery",
        "benchmark_claim_eligible": (
            benchmark_claim_eligible
        ),
    }


def test_annotation_source_filename_is_deterministic() -> None:
    """Stable metadata should produce a stable filename."""

    observed = annotation_source_filename(
        run_id="run-001",
        family_id="FP_0001",
        condition="standard",
    )

    assert observed == (
        "run-001_FP_0001_standard.json"
    )


@pytest.mark.parametrize(
    (
        "run_id",
        "family_id",
        "condition",
    ),
    [
        (
            "..",
            "FP_0001",
            "standard",
        ),
        (
            "run-001",
            "../FP_0001",
            "standard",
        ),
        (
            "run-001",
            "FP_0001",
            "standard/other",
        ),
    ],
)
def test_annotation_source_filename_rejects_unsafe_components(
    run_id: str,
    family_id: str,
    condition: str,
) -> None:
    """Filename components must not permit path traversal."""

    with pytest.raises(
        ValueError,
        match="not safe",
    ):
        annotation_source_filename(
            run_id=run_id,
            family_id=family_id,
            condition=condition,
        )


def test_prepare_annotation_sources_builds_expected_payload() -> None:
    """A valid real-schema response should become one source."""

    prepared = prepare_annotation_sources(
        batch=_batch(),
        source_artifact=(
            "results/raw/run-001.json"
        ),
        source_artifact_sha256=(
            "c" * 64
        ),
    )

    assert len(prepared) == 1

    source = prepared[0]

    assert source.run_id == "run-001"
    assert source.request_id == "req-001"
    assert source.family_id == "FP_0001"
    assert source.condition == "standard"

    assert source.filename == (
        "run-001_FP_0001_standard.json"
    )

    assert source.payload[
        "artifact_type"
    ] == ANNOTATION_SOURCE_ARTIFACT_TYPE

    assert source.payload[
        "annotation_source_format_version"
    ] == ANNOTATION_SOURCE_FORMAT_VERSION

    assert source.payload[
        "benchmark_claim_eligible"
    ] is False

    request = source.payload[
        "request"
    ]

    assert isinstance(
        request,
        dict,
    )

    assert request[
        "request_id"
    ] == "req-001"

    assert request[
        "run_id"
    ] == "run-001"

    result = source.payload[
        "result"
    ]

    assert isinstance(
        result,
        dict,
    )

    assert result[
        "status"
    ] == "SUCCESS"

    assert result[
        "run_id"
    ] == "run-001"

    source_metadata = source.payload[
        "source"
    ]

    assert isinstance(
        source_metadata,
        dict,
    )

    assert source_metadata[
        "artifact"
    ] == (
        "results/raw/run-001.json"
    )

    assert source_metadata[
        "artifact_sha256"
    ] == "c" * 64

    assert source_metadata[
        "research_phase"
    ] == "discovery"


def test_prepare_annotation_sources_injects_batch_run_id() -> None:
    """Plan requests without run_id must receive verified batch run_id."""

    batch = _batch()

    requests = batch[
        "plan"
    ]

    assert isinstance(
        requests,
        dict,
    )

    plan_requests = requests[
        "requests"
    ]

    assert isinstance(
        plan_requests,
        list,
    )

    first_request = plan_requests[
        0
    ]

    assert isinstance(
        first_request,
        dict,
    )

    assert "run_id" not in first_request

    prepared = prepare_annotation_sources(
        batch=batch,
        source_artifact="raw.json",
        source_artifact_sha256="d" * 64,
    )

    exported_request = prepared[
        0
    ].payload[
        "request"
    ]

    assert isinstance(
        exported_request,
        dict,
    )

    assert exported_request[
        "run_id"
    ] == "run-001"


def test_prepare_annotation_sources_accepts_matching_request_run_id() -> None:
    """Older request records containing run_id remain supported."""

    request = _request()

    request[
        "run_id"
    ] = "run-001"

    prepared = prepare_annotation_sources(
        batch=_batch(
            requests=[
                request
            ]
        ),
        source_artifact="raw.json",
        source_artifact_sha256="e" * 64,
    )

    exported_request = prepared[
        0
    ].payload[
        "request"
    ]

    assert isinstance(
        exported_request,
        dict,
    )

    assert exported_request[
        "run_id"
    ] == "run-001"


def test_prepare_annotation_sources_preserves_false_claim_eligibility() -> None:
    """Discovery ineligibility must survive source preparation."""

    prepared = prepare_annotation_sources(
        batch=_batch(
            benchmark_claim_eligible=False
        ),
        source_artifact="raw.json",
        source_artifact_sha256="f" * 64,
    )

    assert prepared[
        0
    ].payload[
        "benchmark_claim_eligible"
    ] is False


def test_prepare_annotation_sources_preserves_true_claim_eligibility() -> None:
    """Eligible upstream artifacts must preserve their flag."""

    prepared = prepare_annotation_sources(
        batch=_batch(
            benchmark_claim_eligible=True
        ),
        source_artifact="raw.json",
        source_artifact_sha256="1" * 64,
    )

    assert prepared[
        0
    ].payload[
        "benchmark_claim_eligible"
    ] is True


def test_prepare_annotation_sources_rejects_batch_plan_run_id_mismatch() -> None:
    """Batch and evaluation plan must identify the same run."""

    with pytest.raises(
        ValueError,
        match="Batch/plan run_id mismatch",
    ):
        prepare_annotation_sources(
            batch=_batch(
                plan_run_id="run-other"
            ),
            source_artifact="raw.json",
            source_artifact_sha256="2" * 64,
        )


def test_prepare_annotation_sources_rejects_batch_result_run_id_mismatch() -> None:
    """Every result must belong to the batch run."""

    batch = _batch(
        results=[
            _result(
                run_id="run-other"
            )
        ]
    )

    with pytest.raises(
        ValueError,
        match="Batch/result run_id mismatch",
    ):
        prepare_annotation_sources(
            batch=batch,
            source_artifact="raw.json",
            source_artifact_sha256="3" * 64,
        )


def test_prepare_annotation_sources_rejects_request_run_id_mismatch() -> None:
    """If a request contains run_id, it must agree with the batch."""

    request = _request()

    request[
        "run_id"
    ] = "run-other"

    with pytest.raises(
        ValueError,
        match="Batch/request run_id mismatch",
    ):
        prepare_annotation_sources(
            batch=_batch(
                requests=[
                    request
                ]
            ),
            source_artifact="raw.json",
            source_artifact_sha256="4" * 64,
        )


def test_prepare_annotation_sources_rejects_request_id_mismatch() -> None:
    """A result must exist for every planned request."""

    batch = _batch(
        results=[
            _result(
                request_id="req-other"
            )
        ]
    )

    with pytest.raises(
        ValueError,
        match="No evaluation result exists",
    ):
        prepare_annotation_sources(
            batch=batch,
            source_artifact="raw.json",
            source_artifact_sha256="5" * 64,
        )


def test_prepare_annotation_sources_rejects_metadata_mismatch() -> None:
    """Matched IDs must still agree on bound metadata."""

    batch = _batch(
        results=[
            _result(
                family_id="EU_0001"
            )
        ]
    )

    with pytest.raises(
        ValueError,
        match="binding mismatch",
    ):
        prepare_annotation_sources(
            batch=batch,
            source_artifact="raw.json",
            source_artifact_sha256="6" * 64,
        )


def test_prepare_annotation_sources_rejects_non_success_result() -> None:
    """Failed provider responses must not enter annotation."""

    batch = _batch(
        results=[
            _result(
                status="TIMEOUT"
            )
        ]
    )

    with pytest.raises(
        ValueError,
        match="Only successful responses",
    ):
        prepare_annotation_sources(
            batch=batch,
            source_artifact="raw.json",
            source_artifact_sha256="7" * 64,
        )


def test_prepare_annotation_sources_rejects_blank_response() -> None:
    """Successful results still require response text."""

    batch = _batch(
        results=[
            _result(
                response_text=" "
            )
        ]
    )

    with pytest.raises(
        ValueError,
        match="response_text",
    ):
        prepare_annotation_sources(
            batch=batch,
            source_artifact="raw.json",
            source_artifact_sha256="8" * 64,
        )


def test_prepare_annotation_sources_rejects_duplicate_results() -> None:
    """Each result request ID may occur at most once."""

    duplicate = _result()

    batch = _batch(
        requests=[
            _request(),
            _request(
                request_id="req-002",
                condition="formal",
            ),
        ],
        results=[
            duplicate,
            dict(duplicate),
        ],
    )

    with pytest.raises(
        ValueError,
        match="Duplicate result request_id",
    ):
        prepare_annotation_sources(
            batch=batch,
            source_artifact="raw.json",
            source_artifact_sha256="9" * 64,
        )


def test_prepare_annotation_sources_rejects_result_count_mismatch() -> None:
    """Declared result count must match serialized results."""

    batch = _batch(
        result_count=2
    )

    with pytest.raises(
        ValueError,
        match="result_count",
    ):
        prepare_annotation_sources(
            batch=batch,
            source_artifact="raw.json",
            source_artifact_sha256="a" * 64,
        )


def test_prepare_annotation_sources_rejects_plan_request_count_mismatch() -> None:
    """Declared plan request count must match plan requests."""

    batch = _batch(
        plan_request_count=2
    )

    with pytest.raises(
        ValueError,
        match="request_count",
    ):
        prepare_annotation_sources(
            batch=batch,
            source_artifact="raw.json",
            source_artifact_sha256="b" * 64,
        )


def test_prepare_annotation_sources_rejects_plan_result_length_mismatch() -> None:
    """The completed batch must cover the full request plan."""

    batch = _batch(
        requests=[
            _request(),
            _request(
                request_id="req-002",
                condition="formal",
            ),
        ],
        results=[
            _result()
        ],
    )

    with pytest.raises(
        ValueError,
        match="number of planned requests",
    ):
        prepare_annotation_sources(
            batch=batch,
            source_artifact="raw.json",
            source_artifact_sha256="c" * 64,
        )


def test_prepare_annotation_sources_rejects_blank_source_artifact() -> None:
    """Source provenance label must not be blank."""

    with pytest.raises(
        ValueError,
        match="source_artifact",
    ):
        prepare_annotation_sources(
            batch=_batch(),
            source_artifact=" ",
            source_artifact_sha256="d" * 64,
        )


def test_write_annotation_sources_atomic_writes_json(
    tmp_path: Path,
) -> None:
    """Prepared sources should persist as readable JSON."""

    prepared = prepare_annotation_sources(
        batch=_batch(),
        source_artifact="raw.json",
        source_artifact_sha256="e" * 64,
    )

    paths = write_annotation_sources_atomic(
        output_dir=tmp_path,
        sources=prepared,
    )

    assert len(paths) == 1

    output_path = paths[0]

    assert output_path.exists()

    loaded = json.loads(
        output_path.read_text(
            encoding="utf-8"
        )
    )

    assert loaded[
        "artifact_type"
    ] == ANNOTATION_SOURCE_ARTIFACT_TYPE

    assert loaded[
        "benchmark_claim_eligible"
    ] is False

    request = loaded[
        "request"
    ]

    assert isinstance(
        request,
        dict,
    )

    assert request[
        "run_id"
    ] == "run-001"


def test_write_annotation_sources_atomic_refuses_silent_overwrite(
    tmp_path: Path,
) -> None:
    """Existing source files require explicit overwrite."""

    prepared = prepare_annotation_sources(
        batch=_batch(),
        source_artifact="raw.json",
        source_artifact_sha256="f" * 64,
    )

    write_annotation_sources_atomic(
        output_dir=tmp_path,
        sources=prepared,
    )

    with pytest.raises(
        FileExistsError,
        match="Refusing to overwrite",
    ):
        write_annotation_sources_atomic(
            output_dir=tmp_path,
            sources=prepared,
        )


def test_write_annotation_sources_atomic_allows_explicit_overwrite(
    tmp_path: Path,
) -> None:
    """Explicit overwrite permits deterministic regeneration."""

    prepared = prepare_annotation_sources(
        batch=_batch(),
        source_artifact="raw.json",
        source_artifact_sha256="1" * 64,
    )

    first_paths = (
        write_annotation_sources_atomic(
            output_dir=tmp_path,
            sources=prepared,
        )
    )

    second_paths = (
        write_annotation_sources_atomic(
            output_dir=tmp_path,
            sources=prepared,
            overwrite=True,
        )
    )

    assert first_paths == second_paths
    assert second_paths[0].exists()


def test_write_annotation_sources_rejects_duplicate_output_paths(
    tmp_path: Path,
) -> None:
    """Two prepared records may not target the same file."""

    payload: dict[
        str,
        object,
    ] = {
        "artifact_type": (
            ANNOTATION_SOURCE_ARTIFACT_TYPE
        )
    }

    source = PreparedAnnotationSource(
        run_id="run-001",
        request_id="req-001",
        family_id="FP_0001",
        condition="standard",
        filename="duplicate.json",
        payload=payload,
    )

    duplicate = PreparedAnnotationSource(
        run_id="run-001",
        request_id="req-002",
        family_id="FP_0001",
        condition="standard",
        filename="duplicate.json",
        payload=payload,
    )

    with pytest.raises(
        ValueError,
        match="duplicate output paths",
    ):
        write_annotation_sources_atomic(
            output_dir=tmp_path,
            sources=(
                source,
                duplicate,
            ),
        )


def test_sha256_file_is_deterministic(
    tmp_path: Path,
) -> None:
    """File hashing should be stable and content-sensitive."""

    path = (
        tmp_path
        / "artifact.json"
    )

    path.write_text(
        "hello\n",
        encoding="utf-8",
    )

    first = sha256_file(path)
    second = sha256_file(path)

    assert first == second
    assert len(first) == 64

    path.write_text(
        "different\n",
        encoding="utf-8",
    )

    assert sha256_file(path) != first