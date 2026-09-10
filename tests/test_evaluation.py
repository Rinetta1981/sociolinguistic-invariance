from datetime import UTC, datetime, timedelta

import pytest

from sociolinguistic_invariance.core import TaskType, VariationCondition
from sociolinguistic_invariance.evaluation import (
    DEFAULT_SYSTEM_INSTRUCTION,
    EVALUATION_PROTOCOL_VERSION,
    AttemptRecord,
    EvaluationRequest,
    EvaluationResult,
    EvaluationRun,
    ModelConfiguration,
    ProviderUsage,
    ResponseStatus,
    attempt_record_to_dict,
    build_evaluation_request,
    evaluation_request_to_dict,
    evaluation_result_to_dict,
    evaluation_run_to_dict,
    model_configuration_to_dict,
    new_request_id,
    new_run_id,
    provider_usage_to_dict,
    sha256_text,
    utc_now,
)

PROMPT_TEXT = "Η Μαδρίτη είναι η πρωτεύουσα της Πορτογαλίας. Γιατί;"
PROMPT_SHA256 = sha256_text(PROMPT_TEXT)

STARTED_AT = datetime(
    2026,
    9,
    10,
    12,
    0,
    0,
    tzinfo=UTC,
)

FINISHED_AT = STARTED_AT + timedelta(
    seconds=0.25,
)

ARTIFACT_SHA256 = (
    "ec888b5f47489f7abe029d5fb870feef"
    "0d5e72ccf3afbe7ebbabec558ab3f5b9"
)


def _success_attempt(
    *,
    attempt_number: int = 1,
) -> AttemptRecord:
    return AttemptRecord(
        attempt_number=attempt_number,
        status=ResponseStatus.SUCCESS,
        started_at=STARTED_AT,
        finished_at=FINISHED_AT,
        latency_seconds=0.25,
        provider_request_id="provider_req_123",
    )


def _error_attempt(
    *,
    attempt_number: int = 1,
    status: ResponseStatus = ResponseStatus.PROVIDER_ERROR,
) -> AttemptRecord:
    return AttemptRecord(
        attempt_number=attempt_number,
        status=status,
        started_at=STARTED_AT,
        finished_at=FINISHED_AT,
        latency_seconds=0.25,
        error_type="TemporaryProviderError",
        error_message="Temporary provider failure.",
    )


def _success_result(
    *,
    attempts: tuple[AttemptRecord, ...] | None = None,
) -> EvaluationResult:
    if attempts is None:
        attempts = (
            _success_attempt(),
        )

    return EvaluationResult(
        run_id="run_test",
        request_id="req_test",
        family_id="FP_0001",
        task_type=TaskType.FALSE_PREMISE_CORRECTION,
        condition=VariationCondition.STANDARD,
        provider="example-provider",
        requested_model="example-model",
        returned_model="example-model-2026-09",
        prompt_sha256=PROMPT_SHA256,
        status=ResponseStatus.SUCCESS,
        response_text=(
            "Η Μαδρίτη είναι η πρωτεύουσα της Ισπανίας, "
            "ενώ η Λισαβόνα είναι η πρωτεύουσα της Πορτογαλίας."
        ),
        request_started_at=STARTED_AT,
        response_finished_at=FINISHED_AT,
        latency_seconds=0.25,
        attempts=attempts,
        provider_request_id="provider_req_123",
        finish_reason="stop",
        usage=ProviderUsage(
            input_tokens=20,
            output_tokens=25,
            total_tokens=45,
        ),
    )


def test_evaluation_protocol_constants() -> None:
    assert EVALUATION_PROTOCOL_VERSION == "evaluation-protocol-v0.1"
    assert (
        DEFAULT_SYSTEM_INSTRUCTION
        == "Answer the user's request directly and accurately."
    )


def test_sha256_text_hashes_exact_utf8_text() -> None:
    assert (
        sha256_text("Γεια σου")
        == "38ee752dbbf06da8642eb9b504e456de"
        "4f7661f42b46b29ae9c266c68f1ad04a"
    )


def test_new_run_id_has_expected_format() -> None:
    run_id = new_run_id()

    assert run_id.startswith("run_")
    assert len(run_id) == 36

    int(
        run_id.removeprefix("run_"),
        16,
    )


def test_new_request_id_has_expected_format() -> None:
    request_id = new_request_id()

    assert request_id.startswith("req_")
    assert len(request_id) == 36

    int(
        request_id.removeprefix("req_"),
        16,
    )


def test_utc_now_returns_timezone_aware_datetime() -> None:
    timestamp = utc_now()

    assert timestamp.tzinfo is not None
    assert timestamp.utcoffset() == timedelta(0)


def test_model_configuration_defaults_and_serialization() -> None:
    configuration = ModelConfiguration(
        provider="example-provider",
        requested_model="example-model",
    )

    assert model_configuration_to_dict(configuration) == {
        "provider": "example-provider",
        "requested_model": "example-model",
        "temperature": 0.0,
        "top_p": None,
        "max_output_tokens": 512,
        "seed": None,
        "system_instruction": DEFAULT_SYSTEM_INSTRUCTION,
        "sdk_version": None,
    }


@pytest.mark.parametrize(
    ("provider", "requested_model"),
    [
        ("", "example-model"),
        ("example-provider", "   "),
    ],
)
def test_model_configuration_rejects_blank_required_fields(
    provider: str,
    requested_model: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="must be non-blank",
    ):
        ModelConfiguration(
            provider=provider,
            requested_model=requested_model,
        )


def test_model_configuration_rejects_negative_temperature() -> None:
    with pytest.raises(
        ValueError,
        match="temperature must be non-negative",
    ):
        ModelConfiguration(
            provider="example-provider",
            requested_model="example-model",
            temperature=-0.1,
        )


@pytest.mark.parametrize(
    "top_p",
    [
        -0.1,
        1.1,
    ],
)
def test_model_configuration_rejects_invalid_top_p(
    top_p: float,
) -> None:
    with pytest.raises(
        ValueError,
        match="top_p must be between 0 and 1",
    ):
        ModelConfiguration(
            provider="example-provider",
            requested_model="example-model",
            top_p=top_p,
        )


@pytest.mark.parametrize(
    "max_output_tokens",
    [
        0,
        -1,
    ],
)
def test_model_configuration_rejects_nonpositive_max_tokens(
    max_output_tokens: int,
) -> None:
    with pytest.raises(
        ValueError,
        match="max_output_tokens must be positive",
    ):
        ModelConfiguration(
            provider="example-provider",
            requested_model="example-model",
            max_output_tokens=max_output_tokens,
        )


def test_model_configuration_rejects_blank_system_instruction() -> None:
    with pytest.raises(
        ValueError,
        match="system_instruction must be non-blank",
    ):
        ModelConfiguration(
            provider="example-provider",
            requested_model="example-model",
            system_instruction="   ",
        )


def test_model_configuration_rejects_blank_sdk_version() -> None:
    with pytest.raises(
        ValueError,
        match="sdk_version must be non-blank",
    ):
        ModelConfiguration(
            provider="example-provider",
            requested_model="example-model",
            sdk_version="   ",
        )


def test_evaluation_run_serializes_metadata() -> None:
    configuration = ModelConfiguration(
        provider="example-provider",
        requested_model="example-model",
        sdk_version="1.2.3",
    )

    run = EvaluationRun(
        run_id="run_test",
        artifact_id="pilot_v0.1",
        artifact_path="data/frozen/pilot_v0.1.jsonl",
        artifact_sha256=ARTIFACT_SHA256,
        model_configuration=configuration,
        started_at=STARTED_AT,
        git_commit="365fd1e",
    )

    payload = evaluation_run_to_dict(run)

    assert payload == {
        "run_id": "run_test",
        "artifact_id": "pilot_v0.1",
        "artifact_path": "data/frozen/pilot_v0.1.jsonl",
        "artifact_sha256": ARTIFACT_SHA256,
        "model_configuration": {
            "provider": "example-provider",
            "requested_model": "example-model",
            "temperature": 0.0,
            "top_p": None,
            "max_output_tokens": 512,
            "seed": None,
            "system_instruction": DEFAULT_SYSTEM_INSTRUCTION,
            "sdk_version": "1.2.3",
        },
        "started_at": "2026-09-10T12:00:00Z",
        "git_commit": "365fd1e",
        "evaluation_protocol_version": EVALUATION_PROTOCOL_VERSION,
    }


def test_evaluation_run_rejects_invalid_artifact_hash() -> None:
    configuration = ModelConfiguration(
        provider="example-provider",
        requested_model="example-model",
    )

    with pytest.raises(
        ValueError,
        match="artifact_sha256 must contain exactly 64",
    ):
        EvaluationRun(
            run_id="run_test",
            artifact_id="pilot_v0.1",
            artifact_path="data/frozen/pilot_v0.1.jsonl",
            artifact_sha256="not-a-valid-hash",
            model_configuration=configuration,
            started_at=STARTED_AT,
        )


def test_evaluation_run_rejects_naive_timestamp() -> None:
    configuration = ModelConfiguration(
        provider="example-provider",
        requested_model="example-model",
    )

    with pytest.raises(
        ValueError,
        match="started_at must be timezone-aware",
    ):
        EvaluationRun(
            run_id="run_test",
            artifact_id="pilot_v0.1",
            artifact_path="data/frozen/pilot_v0.1.jsonl",
            artifact_sha256=ARTIFACT_SHA256,
            model_configuration=configuration,
            started_at=datetime(
                2026,
                9,
                10,
                12,
                0,
                0,
            ),
        )


def test_evaluation_run_rejects_blank_git_commit() -> None:
    configuration = ModelConfiguration(
        provider="example-provider",
        requested_model="example-model",
    )

    with pytest.raises(
        ValueError,
        match="git_commit must be non-blank",
    ):
        EvaluationRun(
            run_id="run_test",
            artifact_id="pilot_v0.1",
            artifact_path="data/frozen/pilot_v0.1.jsonl",
            artifact_sha256=ARTIFACT_SHA256,
            model_configuration=configuration,
            started_at=STARTED_AT,
            git_commit="   ",
        )


def test_build_evaluation_request_hashes_exact_prompt() -> None:
    request = build_evaluation_request(
        run_id="run_test",
        family_id="FP_0001",
        task_type=TaskType.FALSE_PREMISE_CORRECTION,
        condition=VariationCondition.STANDARD,
        prompt_text=PROMPT_TEXT,
        order_index=0,
    )

    assert request.run_id == "run_test"
    assert request.request_id.startswith("req_")
    assert request.family_id == "FP_0001"
    assert request.task_type is TaskType.FALSE_PREMISE_CORRECTION
    assert request.condition is VariationCondition.STANDARD
    assert request.prompt_text == PROMPT_TEXT
    assert request.prompt_sha256 == PROMPT_SHA256
    assert request.order_index == 0


def test_evaluation_request_serializes_deterministically() -> None:
    request = EvaluationRequest(
        run_id="run_test",
        request_id="req_test",
        family_id="FP_0001",
        task_type=TaskType.FALSE_PREMISE_CORRECTION,
        condition=VariationCondition.STANDARD,
        prompt_text=PROMPT_TEXT,
        prompt_sha256=PROMPT_SHA256,
        order_index=0,
    )

    assert evaluation_request_to_dict(request) == {
        "run_id": "run_test",
        "request_id": "req_test",
        "family_id": "FP_0001",
        "task_type": "false_premise_correction",
        "condition": "standard",
        "prompt_text": PROMPT_TEXT,
        "prompt_sha256": PROMPT_SHA256,
        "order_index": 0,
    }


def test_evaluation_request_rejects_hash_mismatch() -> None:
    wrong_hash = sha256_text(
        PROMPT_TEXT + " changed"
    )

    with pytest.raises(
        ValueError,
        match="prompt_sha256 does not match prompt_text",
    ):
        EvaluationRequest(
            run_id="run_test",
            request_id="req_test",
            family_id="FP_0001",
            task_type=TaskType.FALSE_PREMISE_CORRECTION,
            condition=VariationCondition.STANDARD,
            prompt_text=PROMPT_TEXT,
            prompt_sha256=wrong_hash,
            order_index=0,
        )


def test_evaluation_request_rejects_negative_order_index() -> None:
    with pytest.raises(
        ValueError,
        match="order_index must be non-negative",
    ):
        EvaluationRequest(
            run_id="run_test",
            request_id="req_test",
            family_id="FP_0001",
            task_type=TaskType.FALSE_PREMISE_CORRECTION,
            condition=VariationCondition.STANDARD,
            prompt_text=PROMPT_TEXT,
            prompt_sha256=PROMPT_SHA256,
            order_index=-1,
        )


def test_evaluation_request_rejects_blank_prompt() -> None:
    with pytest.raises(
        ValueError,
        match="prompt_text must be non-blank",
    ):
        EvaluationRequest(
            run_id="run_test",
            request_id="req_test",
            family_id="FP_0001",
            task_type=TaskType.FALSE_PREMISE_CORRECTION,
            condition=VariationCondition.STANDARD,
            prompt_text="   ",
            prompt_sha256=sha256_text("   "),
            order_index=0,
        )


def test_provider_usage_serializes_counts() -> None:
    usage = ProviderUsage(
        input_tokens=10,
        output_tokens=20,
        total_tokens=30,
    )

    assert provider_usage_to_dict(usage) == {
        "input_tokens": 10,
        "output_tokens": 20,
        "total_tokens": 30,
    }


def test_provider_usage_rejects_negative_input_tokens() -> None:
    with pytest.raises(
        ValueError,
        match="input_tokens must be non-negative",
    ):
        ProviderUsage(
            input_tokens=-1,
        )


def test_provider_usage_rejects_negative_output_tokens() -> None:
    with pytest.raises(
        ValueError,
        match="output_tokens must be non-negative",
    ):
        ProviderUsage(
            output_tokens=-1,
        )


def test_provider_usage_rejects_negative_total_tokens() -> None:
    with pytest.raises(
        ValueError,
        match="total_tokens must be non-negative",
    ):
        ProviderUsage(
            total_tokens=-1,
        )


def test_attempt_record_serializes_execution_evidence() -> None:
    attempt = _success_attempt()

    assert attempt_record_to_dict(attempt) == {
        "attempt_number": 1,
        "status": "SUCCESS",
        "started_at": "2026-09-10T12:00:00Z",
        "finished_at": "2026-09-10T12:00:00.250000Z",
        "latency_seconds": 0.25,
        "provider_request_id": "provider_req_123",
        "error_type": None,
        "error_message": None,
    }


def test_attempt_record_rejects_zero_attempt_number() -> None:
    with pytest.raises(
        ValueError,
        match="attempt_number must be at least 1",
    ):
        AttemptRecord(
            attempt_number=0,
            status=ResponseStatus.SUCCESS,
            started_at=STARTED_AT,
            finished_at=FINISHED_AT,
            latency_seconds=0.25,
        )


def test_attempt_record_rejects_naive_start_timestamp() -> None:
    with pytest.raises(
        ValueError,
        match="started_at must be timezone-aware",
    ):
        AttemptRecord(
            attempt_number=1,
            status=ResponseStatus.SUCCESS,
            started_at=datetime(
                2026,
                9,
                10,
                12,
                0,
                0,
            ),
            finished_at=FINISHED_AT,
            latency_seconds=0.25,
        )


def test_attempt_record_rejects_naive_finish_timestamp() -> None:
    with pytest.raises(
        ValueError,
        match="finished_at must be timezone-aware",
    ):
        AttemptRecord(
            attempt_number=1,
            status=ResponseStatus.SUCCESS,
            started_at=STARTED_AT,
            finished_at=datetime(
                2026,
                9,
                10,
                12,
                0,
                1,
            ),
            latency_seconds=0.25,
        )


def test_attempt_record_rejects_reversed_timestamps() -> None:
    with pytest.raises(
        ValueError,
        match="finished_at must not precede started_at",
    ):
        AttemptRecord(
            attempt_number=1,
            status=ResponseStatus.SUCCESS,
            started_at=FINISHED_AT,
            finished_at=STARTED_AT,
            latency_seconds=0.25,
        )


def test_attempt_record_rejects_negative_latency() -> None:
    with pytest.raises(
        ValueError,
        match="latency_seconds must be non-negative",
    ):
        AttemptRecord(
            attempt_number=1,
            status=ResponseStatus.SUCCESS,
            started_at=STARTED_AT,
            finished_at=FINISHED_AT,
            latency_seconds=-0.01,
        )


@pytest.mark.parametrize(
    (
        "provider_request_id",
        "error_type",
        "error_message",
    ),
    [
        ("   ", None, None),
        (None, "   ", None),
        (None, None, "   "),
    ],
)
def test_attempt_record_rejects_blank_optional_strings(
    provider_request_id: str | None,
    error_type: str | None,
    error_message: str | None,
) -> None:
    with pytest.raises(
        ValueError,
        match="must be non-blank when provided",
    ):
        AttemptRecord(
            attempt_number=1,
            status=ResponseStatus.PROVIDER_ERROR,
            started_at=STARTED_AT,
            finished_at=FINISHED_AT,
            latency_seconds=0.25,
            provider_request_id=provider_request_id,
            error_type=error_type,
            error_message=error_message,
        )


def test_successful_result_serializes_complete_record() -> None:
    result = _success_result()

    payload = evaluation_result_to_dict(result)

    assert result.retry_count == 0

    assert payload["run_id"] == "run_test"
    assert payload["request_id"] == "req_test"
    assert payload["family_id"] == "FP_0001"
    assert payload["task_type"] == "false_premise_correction"
    assert payload["condition"] == "standard"
    assert payload["provider"] == "example-provider"
    assert payload["requested_model"] == "example-model"
    assert payload["returned_model"] == "example-model-2026-09"
    assert payload["prompt_sha256"] == PROMPT_SHA256
    assert payload["status"] == "SUCCESS"
    assert payload["retry_count"] == 0
    assert payload["latency_seconds"] == 0.25
    assert payload["finish_reason"] == "stop"
    assert payload["evaluation_protocol_version"] == (
        EVALUATION_PROTOCOL_VERSION
    )
    assert payload["usage"] == {
        "input_tokens": 20,
        "output_tokens": 25,
        "total_tokens": 45,
    }

    attempts = payload["attempts"]

    assert isinstance(
        attempts,
        list,
    )
    assert len(attempts) == 1


def test_successful_retry_preserves_attempt_history() -> None:
    first_attempt = _error_attempt(
        attempt_number=1,
        status=ResponseStatus.RATE_LIMITED,
    )

    second_attempt = _success_attempt(
        attempt_number=2,
    )

    result = _success_result(
        attempts=(
            first_attempt,
            second_attempt,
        )
    )

    payload = evaluation_result_to_dict(result)

    assert result.retry_count == 1
    assert payload["retry_count"] == 1

    attempts = payload["attempts"]

    assert isinstance(
        attempts,
        list,
    )
    assert len(attempts) == 2
    assert attempts[0]["status"] == "RATE_LIMITED"
    assert attempts[1]["status"] == "SUCCESS"


def test_skipped_result_requires_no_provider_attempt() -> None:
    result = EvaluationResult(
        run_id="run_test",
        request_id="req_test",
        family_id="FP_0001",
        task_type=TaskType.FALSE_PREMISE_CORRECTION,
        condition=VariationCondition.STANDARD,
        provider="example-provider",
        requested_model="example-model",
        prompt_sha256=PROMPT_SHA256,
        status=ResponseStatus.SKIPPED,
        request_started_at=STARTED_AT,
        response_finished_at=STARTED_AT,
        latency_seconds=0.0,
        attempts=(),
    )

    assert result.retry_count == 0
    assert result.status is ResponseStatus.SKIPPED


def test_skipped_result_rejects_provider_attempts() -> None:
    with pytest.raises(
        ValueError,
        match="SKIPPED result must not contain provider attempts",
    ):
        EvaluationResult(
            run_id="run_test",
            request_id="req_test",
            family_id="FP_0001",
            task_type=TaskType.FALSE_PREMISE_CORRECTION,
            condition=VariationCondition.STANDARD,
            provider="example-provider",
            requested_model="example-model",
            prompt_sha256=PROMPT_SHA256,
            status=ResponseStatus.SKIPPED,
            request_started_at=STARTED_AT,
            response_finished_at=FINISHED_AT,
            latency_seconds=0.25,
            attempts=(
                _success_attempt(),
            ),
        )


def test_non_skipped_result_requires_attempt() -> None:
    with pytest.raises(
        ValueError,
        match="non-SKIPPED result must contain at least one attempt",
    ):
        EvaluationResult(
            run_id="run_test",
            request_id="req_test",
            family_id="FP_0001",
            task_type=TaskType.FALSE_PREMISE_CORRECTION,
            condition=VariationCondition.STANDARD,
            provider="example-provider",
            requested_model="example-model",
            prompt_sha256=PROMPT_SHA256,
            status=ResponseStatus.TIMEOUT,
            request_started_at=STARTED_AT,
            response_finished_at=FINISHED_AT,
            latency_seconds=0.25,
            attempts=(),
        )


def test_attempt_numbers_must_be_contiguous() -> None:
    first_attempt = _error_attempt(
        attempt_number=1,
        status=ResponseStatus.RATE_LIMITED,
    )

    third_attempt = _success_attempt(
        attempt_number=3,
    )

    with pytest.raises(
        ValueError,
        match="Attempt numbers must be contiguous and begin at 1",
    ):
        _success_result(
            attempts=(
                first_attempt,
                third_attempt,
            )
        )


def test_final_attempt_status_must_match_result_status() -> None:
    attempt = _error_attempt(
        status=ResponseStatus.PROVIDER_ERROR,
    )

    with pytest.raises(
        ValueError,
        match="Final attempt status must match result status",
    ):
        EvaluationResult(
            run_id="run_test",
            request_id="req_test",
            family_id="FP_0001",
            task_type=TaskType.FALSE_PREMISE_CORRECTION,
            condition=VariationCondition.STANDARD,
            provider="example-provider",
            requested_model="example-model",
            prompt_sha256=PROMPT_SHA256,
            status=ResponseStatus.TIMEOUT,
            request_started_at=STARTED_AT,
            response_finished_at=FINISHED_AT,
            latency_seconds=0.25,
            attempts=(
                attempt,
            ),
        )


@pytest.mark.parametrize(
    "response_text",
    [
        None,
        "   ",
    ],
)
def test_success_requires_nonblank_response_text(
    response_text: str | None,
) -> None:
    with pytest.raises(
        ValueError,
        match="SUCCESS requires a non-blank response_text",
    ):
        EvaluationResult(
            run_id="run_test",
            request_id="req_test",
            family_id="FP_0001",
            task_type=TaskType.FALSE_PREMISE_CORRECTION,
            condition=VariationCondition.STANDARD,
            provider="example-provider",
            requested_model="example-model",
            prompt_sha256=PROMPT_SHA256,
            status=ResponseStatus.SUCCESS,
            request_started_at=STARTED_AT,
            response_finished_at=FINISHED_AT,
            latency_seconds=0.25,
            attempts=(
                _success_attempt(),
            ),
            response_text=response_text,
        )


def test_result_rejects_reversed_timestamps() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "response_finished_at must not precede "
            "request_started_at"
        ),
    ):
        EvaluationResult(
            run_id="run_test",
            request_id="req_test",
            family_id="FP_0001",
            task_type=TaskType.FALSE_PREMISE_CORRECTION,
            condition=VariationCondition.STANDARD,
            provider="example-provider",
            requested_model="example-model",
            prompt_sha256=PROMPT_SHA256,
            status=ResponseStatus.SUCCESS,
            request_started_at=FINISHED_AT,
            response_finished_at=STARTED_AT,
            latency_seconds=0.25,
            attempts=(
                _success_attempt(),
            ),
            response_text="Valid response.",
        )


def test_result_rejects_negative_latency() -> None:
    with pytest.raises(
        ValueError,
        match="latency_seconds must be non-negative",
    ):
        EvaluationResult(
            run_id="run_test",
            request_id="req_test",
            family_id="FP_0001",
            task_type=TaskType.FALSE_PREMISE_CORRECTION,
            condition=VariationCondition.STANDARD,
            provider="example-provider",
            requested_model="example-model",
            prompt_sha256=PROMPT_SHA256,
            status=ResponseStatus.SUCCESS,
            request_started_at=STARTED_AT,
            response_finished_at=FINISHED_AT,
            latency_seconds=-0.1,
            attempts=(
                _success_attempt(),
            ),
            response_text="Valid response.",
        )


def test_provider_error_result_preserves_failure_evidence() -> None:
    attempt = _error_attempt()

    result = EvaluationResult(
        run_id="run_test",
        request_id="req_test",
        family_id="FP_0001",
        task_type=TaskType.FALSE_PREMISE_CORRECTION,
        condition=VariationCondition.STANDARD,
        provider="example-provider",
        requested_model="example-model",
        prompt_sha256=PROMPT_SHA256,
        status=ResponseStatus.PROVIDER_ERROR,
        request_started_at=STARTED_AT,
        response_finished_at=FINISHED_AT,
        latency_seconds=0.25,
        attempts=(
            attempt,
        ),
        error_type="TemporaryProviderError",
        error_message="Temporary provider failure.",
    )

    payload = evaluation_result_to_dict(result)

    assert payload["status"] == "PROVIDER_ERROR"
    assert payload["response_text"] is None
    assert payload["error_type"] == "TemporaryProviderError"
    assert payload["error_message"] == "Temporary provider failure."
    assert payload["retry_count"] == 0