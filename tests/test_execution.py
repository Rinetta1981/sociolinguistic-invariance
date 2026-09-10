import time
from collections.abc import Callable, Sequence

import pytest
from sociolinguistic_invariance.execution import (
    EvaluationExecutor,
    RetryPolicy,
)

from sociolinguistic_invariance.core import (
    TaskType,
    VariationCondition,
)
from sociolinguistic_invariance.evaluation import (
    EvaluationRequest,
    ModelConfiguration,
    ProviderUsage,
    ResponseStatus,
    sha256_text,
)
from sociolinguistic_invariance.provider import (
    ProviderAction,
    ProviderError,
    ProviderInvalidResponseError,
    ProviderRateLimitError,
    ProviderResponse,
    ProviderTimeoutError,
    ScriptedMockProvider,
)

PROMPT_TEXT = "Δώσε μου τρία πρακτικά βήματα."


def _request() -> EvaluationRequest:
    """Create one valid evaluation request."""

    return EvaluationRequest(
        run_id="run_test",
        request_id="req_test",
        family_id="BR_0001",
        task_type=TaskType.BENIGN_REQUEST,
        condition=VariationCondition.STANDARD,
        prompt_text=PROMPT_TEXT,
        prompt_sha256=sha256_text(
            PROMPT_TEXT
        ),
        order_index=0,
    )


def _configuration(
    provider: str = "mock",
) -> ModelConfiguration:
    """Create one valid model configuration."""

    return ModelConfiguration(
        provider=provider,
        requested_model="mock-model-v1",
        temperature=0.0,
        max_output_tokens=512,
    )


def _no_sleep(
    _: float,
) -> None:
    """Test sleep function that never blocks."""

    return None


def _build_executor(
    actions: Sequence[ProviderAction],
    *,
    retry_policy: RetryPolicy | None = None,
    sleep_fn: Callable[[float], None] = _no_sleep,
    monotonic_fn: Callable[[], float] = (
        time.perf_counter
    ),
) -> tuple[
    ScriptedMockProvider,
    EvaluationExecutor,
]:
    """Create a mock provider and matching executor."""

    provider = ScriptedMockProvider(
        actions=actions
    )

    effective_policy = (
        retry_policy
        if retry_policy is not None
        else RetryPolicy(
            max_attempts=1,
            initial_backoff_seconds=0.0,
            max_backoff_seconds=0.0,
        )
    )

    executor = EvaluationExecutor(
        provider=provider,
        configuration=_configuration(),
        retry_policy=effective_policy,
        sleep_fn=sleep_fn,
        monotonic_fn=monotonic_fn,
    )

    return (
        provider,
        executor,
    )


class SequenceMonotonic:
    """Return predetermined monotonic clock values."""

    def __init__(
        self,
        values: Sequence[float],
    ) -> None:
        self._values = list(
            values
        )

    def __call__(self) -> float:
        if not self._values:
            raise AssertionError(
                "No monotonic test values remain."
            )

        return self._values.pop(
            0
        )


def test_retry_policy_defaults() -> None:
    policy = RetryPolicy()

    assert policy.max_attempts == 3
    assert policy.initial_backoff_seconds == 1.0
    assert policy.backoff_multiplier == 2.0
    assert policy.max_backoff_seconds == 8.0


@pytest.mark.parametrize(
    "max_attempts",
    [
        0,
        -1,
    ],
)
def test_retry_policy_rejects_invalid_max_attempts(
    max_attempts: int,
) -> None:
    with pytest.raises(
        ValueError,
        match="max_attempts must be a positive integer",
    ):
        RetryPolicy(
            max_attempts=max_attempts
        )


def test_retry_policy_rejects_negative_initial_backoff() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "initial_backoff_seconds must be "
            "non-negative"
        ),
    ):
        RetryPolicy(
            initial_backoff_seconds=-0.1
        )


@pytest.mark.parametrize(
    "multiplier",
    [
        0.0,
        0.5,
    ],
)
def test_retry_policy_rejects_small_multiplier(
    multiplier: float,
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "backoff_multiplier must be at least 1.0"
        ),
    ):
        RetryPolicy(
            backoff_multiplier=multiplier
        )


def test_retry_policy_rejects_negative_max_backoff() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "max_backoff_seconds must be non-negative"
        ),
    ):
        RetryPolicy(
            initial_backoff_seconds=0.0,
            max_backoff_seconds=-1.0,
        )


def test_retry_policy_rejects_max_below_initial() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "max_backoff_seconds must be greater "
            "than or equal to initial_backoff_seconds"
        ),
    ):
        RetryPolicy(
            initial_backoff_seconds=2.0,
            max_backoff_seconds=1.0,
        )


def test_retry_policy_backoff_is_exponential_and_capped() -> None:
    policy = RetryPolicy(
        max_attempts=5,
        initial_backoff_seconds=0.5,
        backoff_multiplier=2.0,
        max_backoff_seconds=2.0,
    )

    assert (
        policy.backoff_seconds_after_failure(1)
        == 0.5
    )
    assert (
        policy.backoff_seconds_after_failure(2)
        == 1.0
    )
    assert (
        policy.backoff_seconds_after_failure(3)
        == 2.0
    )
    assert (
        policy.backoff_seconds_after_failure(4)
        == 2.0
    )


def test_retry_policy_rejects_invalid_failed_attempt_number() -> None:
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


def test_successful_execution_returns_success_result() -> None:
    provider, executor = _build_executor(
        [
            ProviderResponse(
                text="Επιτυχής απάντηση."
            )
        ]
    )

    result = executor.execute_request(
        _request()
    )

    assert result.status is ResponseStatus.SUCCESS
    assert result.run_id == "run_test"
    assert result.request_id == "req_test"
    assert result.family_id == "BR_0001"
    assert result.provider == "mock"
    assert result.requested_model == "mock-model-v1"
    assert result.response_text == (
        "Επιτυχής απάντηση."
    )
    assert result.error_type is None
    assert result.error_message is None
    assert len(result.attempts) == 1
    assert result.attempts[0].status is (
        ResponseStatus.SUCCESS
    )
    assert result.latency_seconds >= 0
    assert len(provider.calls) == 1


def test_success_preserves_provider_metadata_and_usage() -> None:
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


def test_success_preserves_response_text_exactly() -> None:
    response_text = (
        "  Απάντηση με περιμετρικά κενά.  "
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

    assert result.status is ResponseStatus.SUCCESS
    assert result.response_text == response_text


def test_blank_response_becomes_invalid_response() -> None:
    _, executor = _build_executor(
        [
            ProviderResponse(
                text="   \n"
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
    assert result.error_type == (
        "BlankProviderResponse"
    )
    assert result.error_message == (
        "Provider returned blank response text."
    )
    assert len(result.attempts) == 1
    assert result.attempts[0].status is (
        ResponseStatus.INVALID_RESPONSE
    )


def test_provider_invalid_response_error_maps_to_invalid_response() -> None:
    _, executor = _build_executor(
        [
            ProviderInvalidResponseError(
                "could not parse provider response"
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
        "could not parse provider response"
    )


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
    assert result.error_type == "ProviderError"
    assert result.error_message == (
        "provider failed"
    )


def test_timeout_maps_to_timeout() -> None:
    _, executor = _build_executor(
        [
            ProviderTimeoutError(
                "request timed out"
            )
        ]
    )

    result = executor.execute_request(
        _request()
    )

    assert result.status is ResponseStatus.TIMEOUT
    assert result.attempts[0].status is (
        ResponseStatus.TIMEOUT
    )


def test_rate_limit_maps_to_rate_limited() -> None:
    _, executor = _build_executor(
        [
            ProviderRateLimitError(
                "rate limited"
            )
        ]
    )

    result = executor.execute_request(
        _request()
    )

    assert result.status is (
        ResponseStatus.RATE_LIMITED
    )
    assert result.attempts[0].status is (
        ResponseStatus.RATE_LIMITED
    )


def test_timeout_is_retried_then_succeeds() -> None:
    policy = RetryPolicy(
        max_attempts=2,
        initial_backoff_seconds=0.0,
        max_backoff_seconds=0.0,
    )

    provider, executor = _build_executor(
        [
            ProviderTimeoutError(
                "timed out"
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

    assert result.status is ResponseStatus.SUCCESS
    assert result.response_text == "recovered"
    assert len(result.attempts) == 2
    assert tuple(
        attempt.status
        for attempt in result.attempts
    ) == (
        ResponseStatus.TIMEOUT,
        ResponseStatus.SUCCESS,
    )
    assert result.retry_count == 1
    assert len(provider.calls) == 2


def test_rate_limit_is_retried_then_succeeds() -> None:
    policy = RetryPolicy(
        max_attempts=2,
        initial_backoff_seconds=0.0,
        max_backoff_seconds=0.0,
    )

    provider, executor = _build_executor(
        [
            ProviderRateLimitError(
                "rate limited"
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

    assert result.status is ResponseStatus.SUCCESS
    assert tuple(
        attempt.status
        for attempt in result.attempts
    ) == (
        ResponseStatus.RATE_LIMITED,
        ResponseStatus.SUCCESS,
    )
    assert len(provider.calls) == 2


def test_retry_backoff_schedule_is_applied() -> None:
    sleep_calls: list[float] = []

    def record_sleep(
        seconds: float,
    ) -> None:
        sleep_calls.append(
            seconds
        )

    policy = RetryPolicy(
        max_attempts=3,
        initial_backoff_seconds=0.5,
        backoff_multiplier=2.0,
        max_backoff_seconds=5.0,
    )

    _, executor = _build_executor(
        [
            ProviderTimeoutError(
                "timeout"
            ),
            ProviderRateLimitError(
                "rate limit"
            ),
            ProviderResponse(
                text="success"
            ),
        ],
        retry_policy=policy,
        sleep_fn=record_sleep,
    )

    result = executor.execute_request(
        _request()
    )

    assert result.status is ResponseStatus.SUCCESS
    assert sleep_calls == [
        0.5,
        1.0,
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

    assert result.status is ResponseStatus.TIMEOUT
    assert result.response_text is None
    assert len(result.attempts) == 3
    assert result.retry_count == 2
    assert len(provider.calls) == 3

    assert tuple(
        attempt.attempt_number
        for attempt in result.attempts
    ) == (
        1,
        2,
        3,
    )

    assert tuple(
        attempt.status
        for attempt in result.attempts
    ) == (
        ResponseStatus.TIMEOUT,
        ResponseStatus.TIMEOUT,
        ResponseStatus.TIMEOUT,
    )

    assert result.error_type == (
        "ProviderTimeoutError"
    )
    assert result.error_message == (
        "timeout three"
    )


def test_mixed_retryable_failures_preserve_status_history() -> None:
    policy = RetryPolicy(
        max_attempts=3,
        initial_backoff_seconds=0.0,
        max_backoff_seconds=0.0,
    )

    _, executor = _build_executor(
        [
            ProviderTimeoutError(
                "timeout"
            ),
            ProviderRateLimitError(
                "rate limit one"
            ),
            ProviderRateLimitError(
                "rate limit two"
            ),
        ],
        retry_policy=policy,
    )

    result = executor.execute_request(
        _request()
    )

    assert result.status is (
        ResponseStatus.RATE_LIMITED
    )

    assert tuple(
        attempt.status
        for attempt in result.attempts
    ) == (
        ResponseStatus.TIMEOUT,
        ResponseStatus.RATE_LIMITED,
        ResponseStatus.RATE_LIMITED,
    )


def test_generic_provider_error_is_not_retried() -> None:
    policy = RetryPolicy(
        max_attempts=3,
        initial_backoff_seconds=0.0,
        max_backoff_seconds=0.0,
    )

    provider, executor = _build_executor(
        [
            ProviderError(
                "permanent provider error"
            ),
            ProviderResponse(
                text="should not execute"
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
    assert len(provider.calls) == 1
    assert provider.remaining_action_count == 1


def test_blank_response_is_not_retried() -> None:
    policy = RetryPolicy(
        max_attempts=3,
        initial_backoff_seconds=0.0,
        max_backoff_seconds=0.0,
    )

    provider, executor = _build_executor(
        [
            ProviderResponse(
                text=""
            ),
            ProviderResponse(
                text="should not execute"
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
    assert len(provider.calls) == 1
    assert provider.remaining_action_count == 1


def test_empty_provider_error_message_is_normalized() -> None:
    _, executor = _build_executor(
        [
            ProviderTimeoutError()
        ]
    )

    result = executor.execute_request(
        _request()
    )

    assert result.error_type == (
        "ProviderTimeoutError"
    )
    assert result.error_message == (
        "ProviderTimeoutError"
    )


def test_attempt_and_total_latency_use_monotonic_clock() -> None:
    monotonic = SequenceMonotonic(
        [
            10.0,
            10.1,
            10.4,
            10.7,
        ]
    )

    _, executor = _build_executor(
        [
            ProviderResponse(
                text="response"
            )
        ],
        monotonic_fn=monotonic,
    )

    result = executor.execute_request(
        _request()
    )

    assert result.attempts[
        0
    ].latency_seconds == pytest.approx(
        0.3
    )

    assert result.latency_seconds == pytest.approx(
        0.7
    )


def test_monotonic_clock_cannot_move_backward() -> None:
    monotonic = SequenceMonotonic(
        [
            10.0,
            10.1,
            10.0,
        ]
    )

    _, executor = _build_executor(
        [
            ProviderResponse(
                text="response"
            )
        ],
        monotonic_fn=monotonic,
    )

    with pytest.raises(
        RuntimeError,
        match="Monotonic clock moved backwards",
    ):
        executor.execute_request(
            _request()
        )


def test_unexpected_provider_exception_propagates() -> None:
    provider = ScriptedMockProvider(
        actions=[]
    )

    executor = EvaluationExecutor(
        provider=provider,
        configuration=_configuration(),
        retry_policy=RetryPolicy(
            max_attempts=1,
            initial_backoff_seconds=0.0,
            max_backoff_seconds=0.0,
        ),
        sleep_fn=_no_sleep,
    )

    with pytest.raises(
        RuntimeError,
        match="Mock provider script is exhausted",
    ):
        executor.execute_request(
            _request()
        )