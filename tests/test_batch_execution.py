import json
from pathlib import Path
from typing import Any

import pytest

from sociolinguistic_invariance.batch_execution import (
    RAW_RESULTS_FORMAT_VERSION,
    build_raw_results_payload,
    count_result_statuses,
    default_raw_results_path,
    execute_evaluation_plan,
    write_raw_results_atomic,
)
from sociolinguistic_invariance.evaluation import (
    EvaluationResult,
    ModelConfiguration,
    ResponseStatus,
)
from sociolinguistic_invariance.evaluation_plan import (
    EvaluationPlan,
    build_evaluation_plan,
)
from sociolinguistic_invariance.execution import (
    EvaluationExecutor,
    RetryPolicy,
)
from sociolinguistic_invariance.provenance import (
    GitProvenance,
)
from sociolinguistic_invariance.provider import (
    ProviderAction,
    ProviderError,
    ProviderResponse,
    ScriptedMockProvider,
)

ARTIFACT_PATH = Path(
    "data/frozen/pilot_v0.1.jsonl"
)

MANIFEST_PATH = Path(
    "data/frozen/pilot_v0.1.manifest.json"
)

VALID_COMMIT = "a" * 40
VALID_STATUS_SHA256 = "b" * 64


def _plan(
    run_id: str = "run_batch_test",
) -> EvaluationPlan:
    """Create the real frozen pilot evaluation plan."""

    return build_evaluation_plan(
        run_id=run_id,
        artifact_path=ARTIFACT_PATH,
        manifest_path=MANIFEST_PATH,
        randomized=False,
        order_seed=None,
    )


def _configuration(
    provider: str = "mock",
) -> ModelConfiguration:
    """Create a mock model configuration."""

    return ModelConfiguration(
        provider=provider,
        requested_model="mock-model-v1",
        temperature=0.0,
        max_output_tokens=512,
    )


def _success_actions(
    count: int,
) -> list[ProviderAction]:
    """Create deterministic successful mock actions."""

    return [
        ProviderResponse(
            text=f"Mock response {index}.",
            provider_request_id=(
                f"mock-request-{index}"
            ),
        )
        for index in range(
            count
        )
    ]


def _executor(
    actions: list[ProviderAction],
) -> EvaluationExecutor:
    """Create a zero-wait mock executor."""

    provider = ScriptedMockProvider(
        actions=actions
    )

    return EvaluationExecutor(
        provider=provider,
        configuration=_configuration(),
        retry_policy=RetryPolicy(
            max_attempts=1,
            initial_backoff_seconds=0.0,
            max_backoff_seconds=0.0,
        ),
        sleep_fn=lambda _: None,
    )


def _clean_provenance() -> GitProvenance:
    """Create deterministic clean test provenance."""

    return GitProvenance(
        available=True,
        commit=VALID_COMMIT,
        worktree_clean=True,
        status_entry_count=0,
        status_sha256=VALID_STATUS_SHA256,
    )


def _successful_results(
    plan: EvaluationPlan,
) -> tuple[EvaluationResult, ...]:
    """Execute a completely successful mock plan."""

    return execute_evaluation_plan(
        plan=plan,
        executor=_executor(
            _success_actions(
                plan.request_count
            )
        ),
    )


def _load_json(
    path: Path,
) -> dict[str, Any]:
    """Load a persisted JSON object."""

    raw_payload = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    assert isinstance(
        raw_payload,
        dict,
    )

    return raw_payload


def test_execute_plan_returns_one_result_per_request() -> None:
    plan = _plan()

    results = _successful_results(
        plan
    )

    assert len(results) == 12
    assert len(results) == plan.request_count


def test_execute_plan_preserves_request_order() -> None:
    plan = _plan()

    results = _successful_results(
        plan
    )

    assert tuple(
        result.request_id
        for result in results
    ) == tuple(
        request.request_id
        for request in plan.requests
    )


def test_execute_plan_preserves_prompt_identity() -> None:
    plan = _plan()

    results = _successful_results(
        plan
    )

    assert tuple(
        result.prompt_sha256
        for result in results
    ) == tuple(
        request.prompt_sha256
        for request in plan.requests
    )


def test_execute_plan_can_preserve_failure_among_successes() -> None:
    plan = _plan()

    actions = _success_actions(
        plan.request_count
    )

    actions[4] = ProviderError(
        "mock provider failure"
    )

    results = execute_evaluation_plan(
        plan=plan,
        executor=_executor(
            actions
        ),
    )

    assert len(results) == 12

    assert results[
        4
    ].status is ResponseStatus.PROVIDER_ERROR

    assert sum(
        result.status is ResponseStatus.SUCCESS
        for result in results
    ) == 11


def test_count_result_statuses_includes_all_statuses() -> None:
    plan = _plan()

    actions = _success_actions(
        plan.request_count
    )

    actions[0] = ProviderError(
        "failure"
    )

    results = execute_evaluation_plan(
        plan=plan,
        executor=_executor(
            actions
        ),
    )

    counts = count_result_statuses(
        results
    )

    assert counts == {
        "SUCCESS": 11,
        "PROVIDER_ERROR": 1,
        "TIMEOUT": 0,
        "RATE_LIMITED": 0,
        "INVALID_RESPONSE": 0,
        "SKIPPED": 0,
    }


def test_count_result_statuses_accepts_empty_sequence() -> None:
    counts = count_result_statuses(
        ()
    )

    assert counts == {
        "SUCCESS": 0,
        "PROVIDER_ERROR": 0,
        "TIMEOUT": 0,
        "RATE_LIMITED": 0,
        "INVALID_RESPONSE": 0,
        "SKIPPED": 0,
    }


def test_build_raw_payload_is_self_contained() -> None:
    plan = _plan()

    configuration = _configuration()

    results = _successful_results(
        plan
    )

    payload = build_raw_results_payload(
        plan=plan,
        configuration=configuration,
        provenance=_clean_provenance(),
        results=results,
    )

    assert payload["artifact_type"] == (
        "raw_evaluation_results"
    )

    assert payload[
        "raw_results_format_version"
    ] == RAW_RESULTS_FORMAT_VERSION

    assert payload["run_id"] == (
        "run_batch_test"
    )

    assert payload["result_count"] == 12

    status_counts = payload[
        "status_counts"
    ]

    assert isinstance(
        status_counts,
        dict,
    )

    assert status_counts["SUCCESS"] == 12

    serialized_results = payload[
        "results"
    ]

    assert isinstance(
        serialized_results,
        list,
    )

    assert len(
        serialized_results
    ) == 12

    serialized_plan = payload[
        "plan"
    ]

    assert isinstance(
        serialized_plan,
        dict,
    )

    assert serialized_plan[
        "request_count"
    ] == 12


def test_build_raw_payload_rejects_result_count_mismatch() -> None:
    plan = _plan()

    results = _successful_results(
        plan
    )

    with pytest.raises(
        ValueError,
        match=(
            "Evaluation result count does not "
            "match evaluation plan request count"
        ),
    ):
        build_raw_results_payload(
            plan=plan,
            configuration=_configuration(),
            provenance=_clean_provenance(),
            results=results[:-1],
        )


def test_build_raw_payload_rejects_result_order_mismatch() -> None:
    plan = _plan()

    results = list(
        _successful_results(
            plan
        )
    )

    results[
        0
    ], results[
        1
    ] = results[
        1
    ], results[
        0
    ]

    with pytest.raises(
        ValueError,
        match=(
            "Evaluation result order does not "
            "match evaluation plan"
        ),
    ):
        build_raw_results_payload(
            plan=plan,
            configuration=_configuration(),
            provenance=_clean_provenance(),
            results=results,
        )


def test_build_raw_payload_rejects_provider_mismatch() -> None:
    plan = _plan()

    results = _successful_results(
        plan
    )

    with pytest.raises(
        ValueError,
        match=(
            "Evaluation result provider does not "
            "match model configuration"
        ),
    ):
        build_raw_results_payload(
            plan=plan,
            configuration=_configuration(
                provider="different-provider"
            ),
            provenance=_clean_provenance(),
            results=results,
        )


def test_default_raw_results_path() -> None:
    assert default_raw_results_path(
        "run_abc"
    ) == Path(
        "results/raw/run_abc.json"
    )


def test_default_raw_results_path_rejects_blank_run_id() -> None:
    with pytest.raises(
        ValueError,
        match="run_id must be non-blank",
    ):
        default_raw_results_path(
            "   "
        )


def test_write_raw_results_creates_json(
    tmp_path: Path,
) -> None:
    output_path = (
        tmp_path
        / "nested"
        / "results.json"
    )

    payload: dict[str, object] = {
        "test": True,
        "count": 12,
    }

    write_raw_results_atomic(
        path=output_path,
        payload=payload,
    )

    assert output_path.exists()

    assert _load_json(
        output_path
    ) == payload


def test_write_raw_results_protects_existing_file(
    tmp_path: Path,
) -> None:
    output_path = (
        tmp_path
        / "results.json"
    )

    output_path.write_text(
        "original",
        encoding="utf-8",
    )

    with pytest.raises(
        FileExistsError,
        match="Raw result file already exists",
    ):
        write_raw_results_atomic(
            path=output_path,
            payload={
                "replacement": True
            },
        )

    assert output_path.read_text(
        encoding="utf-8"
    ) == "original"


def test_write_raw_results_overwrite_is_explicit(
    tmp_path: Path,
) -> None:
    output_path = (
        tmp_path
        / "results.json"
    )

    output_path.write_text(
        "old",
        encoding="utf-8",
    )

    write_raw_results_atomic(
        path=output_path,
        payload={
            "new": True
        },
        overwrite=True,
    )

    assert _load_json(
        output_path
    ) == {
        "new": True
    }