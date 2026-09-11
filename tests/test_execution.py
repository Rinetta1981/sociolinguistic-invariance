import math
import time
from collections.abc import Callable

import pytest

from sociolinguistic_invariance.core import TaskType, VariationCondition
from sociolinguistic_invariance.evaluation import (
    EvaluationRequest,
    ModelConfiguration,
    ProviderUsage,
    ResponseStatus,
    sha256_text,
)
from sociolinguistic_invariance.execution import EvaluationExecutor, RetryPolicy
from sociolinguistic_invariance.provider import (
    ProviderAction,
    ProviderError,
    ProviderInvalidResponseError,
    ProviderRateLimitError,
    ProviderResponse,
    ProviderTimeoutError,
    ScriptedMockProvider,
)

PROMPT_TEXT = "Η Μαδρίτη είναι η πρωτεύουσα της Πορτογαλίας. Γιατί;"


def _request() -> EvaluationRequest:
    """Create one valid evaluation request."""

    return EvaluationRequest(
        run_id="run_execution_test",
        request_id="req_execution_test",
        family_id="FP_0001",
        task_type=TaskType.FALSE_PREMISE_CORRECTION,
        condition=VariationCondition.STANDARD,
        prompt_text=PROMPT_TEXT,
        prompt_sha256=sha256_text(PROMPT_TEXT),
        order_index=0,
    )


def _configuration(
    *,
    provider: str = "mock",
) -> ModelConfiguration:
    """Create one valid model configuration."""

    return ModelConfiguration(
        provider=provider,
        requested_model="mock-model-v1",
        temperature=0.0,
        top_p=None,
        max_output_tokens=512,
        seed=None,
        system_instruction="Answer the user's request directly and accurately.",
        sdk_version=None,
    )


def _build_executor(
    actions: list[ProviderAction],
    *,
    retry_policy: RetryPolicy | None = None,
    sleep_fn: Callable[[float], None] | None = None,
    monotonic_fn: Callable[[], float] | None = None,
) -> tuple[ScriptedMockProvider, EvaluationExecutor]:
    """Create a mock provider and executor."""

    provider = ScriptedMockProvider(
        actions=actions
    )

    executor = EvaluationExecutor(
        provider=provider,
        configuration=_configuration(),
        retry_policy=retry_policy,
        sleep_fn=(
            sleep_fn
            if sleep_fn is not None
            else lambda _: None
        ),
        monotonic_fn=(
            monotonic_fn
            if monotonic_fn is not None
            else time.perf_counter
        ),
    )

    return provider, executor


def _sequence_clock(
    values: list[float],
) -> Callable[[], float]:
    """Return a deterministic monotonic clock."""

    iterator = iter(
        values
    )

    def clock() -> float:
        return next(
            iterator
        )

    return clock


def test_retry_policy_defaults() -> None:
    policy = RetryPolicy()

    assert policy.max_attempts == 3
    assert policy.initial_backoff_seconds == 1.0
    assert policy.backoff_multiplier == 2.0
    assert policy.max_backoff_seconds == 8.0


def test_retry_policy_rejects_zero_max_attempts() -> None:
    with pytest.raises(
        ValueError,
        match="max_attempts must be a positive integer",
    ):
        RetryPolicy(
            max_attempts=0
        )


def test_retry_policy_rejects_boolean_max_attempts() -> None:
    with pytest.raises(
        ValueError,
        match="max_attempts must be a positive integer",
    ):
        RetryPolicy(
            max_attempts=True
        )


def test_retry_policy_rejects_negative_initial_backoff() -> None:
    with pytest.raises(
        ValueError,
        match="initial_backoff_seconds must be non-negative",
    ):
        RetryPolicy(
            initial_backoff_seconds=-0.1
        )


def test_retry_policy_rejects_nonfinite_initial_backoff() -> None:
    with pytest.raises(
        ValueError,
        match="initial_backoff_seconds must be finite",
    ):
        RetryPolicy(
            initial_backoff_seconds=math.inf
        )


def test_retry_policy_rejects_multiplier_below_one() -> None:
    with pytest.raises(
        ValueError,
        match="backoff_multiplier must be at least 1.0",
    ):
        RetryPolicy(
            backoff_multiplier=0.9
        )


def test_retry_policy_rejects_nonfinite_multiplier() -> None:
    with pytest.raises(
        ValueError,
        match="backoff_multiplier must be finite",
    ):
        RetryPolicy(
            backoff_multiplier=math.nan
        )


def test_retry_policy_rejects_negative_max_backoff() -> None:
    with pytest.raises(
        ValueError,
        match="max_backoff_seconds must be non-negative",
    ):
        RetryPolicy(
            initial_backoff_seconds=0.0,
            max_backoff_seconds=-0.1,
        )


def test_retry_policy_rejects_max_backoff_below_initial() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "max_backoff_seconds must be greater than "
            "or equal to initial_backoff_seconds"
        ),
    ):
        RetryPolicy(
            initial_backoff_seconds=2.0,
            max_backoff_seconds=1.0,
        )


def test_retry_policy_backoff_is_exponential_and_capped() -> None:
    policy = RetryPolicy(
        initial_backoff_seconds=1.0,
        backoff_multiplier=2.0,
        max_backoff_seconds=3.0,
    )

    assert policy.backoff_seconds_after_failure(
        1
    ) == 1.0

    assert policy.backoff_seconds_after_failure(
        2
    ) == 2.0

    assert policy.backoff_seconds_after_failure(
        3
    ) == 3.0

    assert policy.backoff_seconds_after_failure(
        4
    ) == 3.0


def test_retry_policy_backoff_rejects_zero_attempt_number() -> None:
    policy = RetryPolicy()

    with pytest.raises(
        ValueError,
        match=(
            "failed_attempt_number must be "
            "a positive integer"
        ),
    ):
        policy.backoff_seconds_after_failure(
            0
        )


def test_executor_rejects_provider_configuration_mismatch() -> None:
    provider = ScriptedMockProvider(
        provider_name="mock",
        actions=[
            ProviderResponse(
                text="response"
            )
        ],
    )

    with pytest.raises(
        ValueError,
        match=(
            "Model configuration provider does not "
            "match provider adapter"
        ),
    ):
        EvaluationExecutor(
            provider=provider,
            configuration=_configuration(
                provider="different-provider"
            ),
        )


def test_success_preserves_request_identity_and_status() -> None:
    _, executor = _build_executor(
        [
            ProviderResponse(
                text="response"
            )
        ]
    )

    request = _request()

    result = executor.execute_request(
        request
    )

    assert result.run_id == request.run_id
    assert result.request_id == request.request_id
    assert result.family_id == request.family_id
    assert result.task_type is request.task_type
    assert result.condition is request.condition
    assert (
        result.prompt_sha256
        == request.prompt_sha256
    )

    assert result.provider == "mock"

    assert result.requested_model == (
        "mock-model-v1"
    )

    assert result.status is (
        ResponseStatus.SUCCESS
    )

    assert len(
        result.attempts
    ) == 1

    assert result.attempts[
        0
    ].status is ResponseStatus.SUCCESS


def test_success_preserves_response_text_exactly() -> None:
    response_text = (
        "  exact response text  "
    )

    _, executor = _build_executor(
        [
            ProviderResponse(
                text=response_text
            )
        ]
    )

    result = executor.execute_request(
        _request()
    )

    assert result.status is (
        ResponseStatus.SUCCESS
    )

    assert result.response_text == (
        response_text
    )


def test_success_preserves_provider_request_id_and_usage() -> None:
    usage = ProviderUsage(
        input_tokens=20,
        output_tokens=10,
        total_tokens=30,
    )

    _, executor = _build_executor(
        [
            ProviderResponse(
                text="response",
                provider_request_id="provider-123",
                usage=usage,
            )
        ]
    )

    result = executor.execute_request(
        _request()
    )

    assert result.provider_request_id == (
        "provider-123"
    )

    assert result.usage == usage

    assert result.attempts[
        0
    ].provider_request_id == "provider-123"


def test_blank_response_becomes_invalid_response() -> None:
    _, executor = _build_executor(
        [
            ProviderResponse(
                text="   ",
                provider_request_id="provider-blank",
            )
        ]
    )

    result = executor.execute_request(
        _request()
    )

    assert result.status is (
        ResponseStatus.INVALID_RESPONSE
    )

    assert result.response_text is None

    assert result.provider_request_id == (
        "provider-blank"
    )

    assert result.error_type == (
        "BlankProviderResponse"
    )

    assert result.error_message == (
        "Provider returned blank response text."
    )

    assert len(
        result.attempts
    ) == 1

    assert result.attempts[
        0
    ].status is ResponseStatus.INVALID_RESPONSE


def test_generic_provider_error_maps_to_provider_error() -> None:
    _, executor = _build_executor(
        [
            ProviderError(
                "provider failed"
            )
        ]
    )

    result = executor.execute_request(
        _request()
    )

    assert result.status is (
        ResponseStatus.PROVIDER_ERROR
    )

    assert result.response_text is None

    assert result.error_type == (
        "ProviderError"
    )

    assert result.error_message == (
        "provider failed"
    )

    assert len(
        result.attempts
    ) == 1


def test_invalid_response_error_maps_to_invalid_response() -> None:
    _, executor = _build_executor(
        [
            ProviderInvalidResponseError(
                "invalid provider response"
            )
        ]
    )

    result = executor.execute_request(
        _request()
    )

    assert result.status is (
        ResponseStatus.INVALID_RESPONSE
    )

    assert result.error_type == (
        "ProviderInvalidResponseError"
    )

    assert result.error_message == (
        "invalid provider response"
    )

    assert len(
        result.attempts
    ) == 1


def test_timeout_error_maps_to_timeout() -> None:
    policy = RetryPolicy(
        max_attempts=1,
        initial_backoff_seconds=0.0,
        max_backoff_seconds=0.0,
    )

    _, executor = _build_executor(
        [
            ProviderTimeoutError(
                "timed out"
            )
        ],
        retry_policy=policy,
    )

    result = executor.execute_request(
        _request()
    )

    assert result.status is (
        ResponseStatus.TIMEOUT
    )

    assert result.error_type == (
        "ProviderTimeoutError"
    )

    assert result.error_message == (
        "timed out"
    )

    assert len(
        result.attempts
    ) == 1


def test_rate_limit_error_maps_to_rate_limited() -> None:
    policy = RetryPolicy(
        max_attempts=1,
        initial_backoff_seconds=0.0,
        max_backoff_seconds=0.0,
    )

    _, executor = _build_executor(
        [
            ProviderRateLimitError(
                "rate limited"
            )
        ],
        retry_policy=policy,
    )

    result = executor.execute_request(
        _request()
    )

    assert result.status is (
        ResponseStatus.RATE_LIMITED
    )

    assert result.error_type == (
        "ProviderRateLimitError"
    )

    assert result.error_message == (
        "rate limited"
    )

    assert len(
        result.attempts
    ) == 1


def test_timeout_is_retried_then_succeeds() -> None:
    policy = RetryPolicy(
        max_attempts=2,
        initial_backoff_seconds=0.0,
        max_backoff_seconds=0.0,
    )

    provider, executor = _build_executor(
        [
            ProviderTimeoutError(
                "temporary timeout"
            ),
            ProviderResponse(
                text="recovered"
            ),
        ],
        retry_policy=policy,
    )

    result = executor.execute_request(
        _request()
    )

    assert result.status is (
        ResponseStatus.SUCCESS
    )

    assert result.response_text == (
        "recovered"
    )

    assert len(
        result.attempts
    ) == 2

    assert result.attempts[
        0
    ].status is ResponseStatus.TIMEOUT

    assert result.attempts[
        1
    ].status is ResponseStatus.SUCCESS

    assert result.retry_count == 1

    assert len(
        provider.calls
    ) == 2


def test_rate_limit_is_retried_then_succeeds() -> None:
    policy = RetryPolicy(
        max_attempts=2,
        initial_backoff_seconds=0.0,
        max_backoff_seconds=0.0,
    )

    provider, executor = _build_executor(
        [
            ProviderRateLimitError(
                "temporary rate limit"
            ),
            ProviderResponse(
                text="recovered"
            ),
        ],
        retry_policy=policy,
    )

    result = executor.execute_request(
        _request()
    )

    assert result.status is (
        ResponseStatus.SUCCESS
    )

    assert result.response_text == (
        "recovered"
    )

    assert len(
        result.attempts
    ) == 2

    assert result.attempts[
        0
    ].status is ResponseStatus.RATE_LIMITED

    assert result.attempts[
        1
    ].status is ResponseStatus.SUCCESS

    assert len(
        provider.calls
    ) == 2


def test_retry_uses_expected_backoff_schedule() -> None:
    sleeps: list[float] = []

    policy = RetryPolicy(
        max_attempts=3,
        initial_backoff_seconds=0.5,
        backoff_multiplier=2.0,
        max_backoff_seconds=4.0,
    )

    _, executor = _build_executor(
        [
            ProviderTimeoutError(
                "first failure"
            ),
            ProviderRateLimitError(
                "second failure"
            ),
            ProviderResponse(
                text="success"
            ),
        ],
        retry_policy=policy,
        sleep_fn=sleeps.append,
    )

    result = executor.execute_request(
        _request()
    )

    assert result.status is (
        ResponseStatus.SUCCESS
    )

    assert sleeps == [
        0.5,
        1.0,
    ]

    assert [
        attempt.status
        for attempt in result.attempts
    ] == [
        ResponseStatus.TIMEOUT,
        ResponseStatus.RATE_LIMITED,
        ResponseStatus.SUCCESS,
    ]


def test_retry_exhaustion_preserves_all_attempts() -> None:
    policy = RetryPolicy(
        max_attempts=3,
        initial_backoff_seconds=0.0,
        max_backoff_seconds=0.0,
    )

    provider, executor = _build_executor(
        [
            ProviderTimeoutError(
                "timeout one"
            ),
            ProviderTimeoutError(
                "timeout two"
            ),
            ProviderTimeoutError(
                "timeout three"
            ),
        ],
        retry_policy=policy,
    )

    result = executor.execute_request(
        _request()
    )

    assert result.status is (
        ResponseStatus.TIMEOUT
    )

    assert result.error_message == (
        "timeout three"
    )

    assert len(
        result.attempts
    ) == 3

    assert result.retry_count == 2

    assert all(
        attempt.status is ResponseStatus.TIMEOUT
        for attempt in result.attempts
    )

    assert len(
        provider.calls
    ) == 3


def test_generic_provider_error_is_not_retried() -> None:
    policy = RetryPolicy(
        max_attempts=3,
        initial_backoff_seconds=0.0,
        max_backoff_seconds=0.0,
    )

    provider, executor = _build_executor(
        [
            ProviderError(
                "permanent failure"
            ),
            ProviderResponse(
                text="should not be used"
            ),
        ],
        retry_policy=policy,
    )

    result = executor.execute_request(
        _request()
    )

    assert result.status is (
        ResponseStatus.PROVIDER_ERROR
    )

    assert len(
        result.attempts
    ) == 1

    assert len(
        provider.calls
    ) == 1

    assert (
        provider.remaining_action_count
        == 1
    )


def test_blank_provider_response_is_not_retried() -> None:
    policy = RetryPolicy(
        max_attempts=3,
        initial_backoff_seconds=0.0,
        max_backoff_seconds=0.0,
    )

    provider, executor = _build_executor(
        [
            ProviderResponse(
                text="   "
            ),
            ProviderResponse(
                text="should not be used"
            ),
        ],
        retry_policy=policy,
    )

    result = executor.execute_request(
        _request()
    )

    assert result.status is (
        ResponseStatus.INVALID_RESPONSE
    )

    assert len(
        result.attempts
    ) == 1

    assert len(
        provider.calls
    ) == 1

    assert (
        provider.remaining_action_count
        == 1
    )


def test_blank_provider_error_message_is_normalized() -> None:
    policy = RetryPolicy(
        max_attempts=1,
        initial_backoff_seconds=0.0,
        max_backoff_seconds=0.0,
    )

    _, executor = _build_executor(
        [
            ProviderError()
        ],
        retry_policy=policy,
    )

    result = executor.execute_request(
        _request()
    )

    assert result.status is (
        ResponseStatus.PROVIDER_ERROR
    )

    assert result.error_type == (
        "ProviderError"
    )

    assert result.error_message == (
        "ProviderError"
    )

    assert result.attempts[
        0
    ].error_message == "ProviderError"


def test_total_latency_uses_monotonic_clock() -> None:
    monotonic_fn = _sequence_clock(
        [
            10.0,
            11.0,
            13.0,
            15.0,
        ]
    )

    _, executor = _build_executor(
        [
            ProviderResponse(
                text="response"
            )
        ],
        monotonic_fn=monotonic_fn,
    )

    result = executor.execute_request(
        _request()
    )

    assert result.attempts[
        0
    ].latency_seconds == 2.0

    assert result.latency_seconds == 5.0


def test_backward_monotonic_clock_is_rejected() -> None:
    monotonic_fn = _sequence_clock(
        [
            10.0,
            11.0,
            10.0,
        ]
    )

    _, executor = _build_executor(
        [
            ProviderResponse(
                text="response"
            )
        ],
        monotonic_fn=monotonic_fn,
    )

    with pytest.raises(
        RuntimeError,
        match="Monotonic clock moved backwards",
    ):
        executor.execute_request(
            _request()
        )


def test_unexpected_provider_exception_propagates() -> None:
    provider, executor = _build_executor(
        []
    )

    with pytest.raises(
        RuntimeError,
        match="Mock provider script is exhausted",
    ):
        executor.execute_request(
            _request()
        )

    assert len(
        provider.calls
    ) == 1


def test_success_preserves_returned_model_and_finish_reason() -> None:
    _, executor = _build_executor(
        [
            ProviderResponse(
                text="response",
                provider_request_id="provider-123",
                returned_model="returned-model-v2",
                finish_reason="end_turn",
            )
        ]
    )

    result = executor.execute_request(
        _request()
    )

    assert result.status is (
        ResponseStatus.SUCCESS
    )

    assert result.returned_model == (
        "returned-model-v2"
    )

    assert result.finish_reason == (
        "end_turn"
    )

    assert result.provider_request_id == (
        "provider-123"
    )


def test_blank_response_preserves_available_provider_metadata() -> None:
    usage = ProviderUsage(
        input_tokens=12,
        output_tokens=0,
        total_tokens=12,
    )

    _, executor = _build_executor(
        [
            ProviderResponse(
                text="   ",
                provider_request_id="provider-blank",
                returned_model="returned-model-v2",
                finish_reason="end_turn",
                usage=usage,
            )
        ]
    )

    result = executor.execute_request(
        _request()
    )

    assert result.status is (
        ResponseStatus.INVALID_RESPONSE
    )

    assert result.returned_model == (
        "returned-model-v2"
    )

    assert result.finish_reason == (
        "end_turn"
    )

    assert result.provider_request_id == (
        "provider-blank"
    )

    assert result.usage == usage