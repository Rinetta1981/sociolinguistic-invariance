import pytest

from sociolinguistic_invariance.core import (
    TaskType,
    VariationCondition,
)
from sociolinguistic_invariance.evaluation import (
    EvaluationRequest,
    ModelConfiguration,
    ProviderUsage,
    sha256_text,
)
from sociolinguistic_invariance.provider import (
    ModelProvider,
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


def test_provider_response_accepts_text_and_usage() -> None:
    usage = ProviderUsage(
        input_tokens=10,
        output_tokens=5,
        total_tokens=15,
    )

    response = ProviderResponse(
        text="Μία απάντηση.",
        provider_request_id="provider-request-1",
        usage=usage,
    )

    assert response.text == "Μία απάντηση."
    assert response.provider_request_id == (
        "provider-request-1"
    )
    assert response.usage == usage


def test_provider_response_allows_blank_text_for_validation_layer() -> None:
    response = ProviderResponse(
        text="",
    )

    assert response.text == ""


def test_provider_response_rejects_blank_provider_request_id() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "provider_request_id must be "
            "non-blank when provided"
        ),
    ):
        ProviderResponse(
            text="response",
            provider_request_id="   ",
        )


def test_mock_provider_satisfies_provider_protocol() -> None:
    provider = ScriptedMockProvider(
        actions=[
            ProviderResponse(
                text="response"
            )
        ]
    )

    assert isinstance(
        provider,
        ModelProvider,
    )


def test_mock_provider_returns_scripted_response() -> None:
    expected = ProviderResponse(
        text="Η δοκιμαστική απάντηση.",
        provider_request_id="mock-1",
    )

    provider = ScriptedMockProvider(
        actions=[
            expected
        ]
    )

    response = provider.generate(
        request=_request(),
        configuration=_configuration(),
    )

    assert response == expected


def test_mock_provider_records_observed_call() -> None:
    provider = ScriptedMockProvider(
        actions=[
            ProviderResponse(
                text="response"
            )
        ]
    )

    provider.generate(
        request=_request(),
        configuration=_configuration(),
    )

    assert len(provider.calls) == 1

    call = provider.calls[0]

    assert call.request_id == "req_test"
    assert call.prompt_text == PROMPT_TEXT
    assert call.requested_model == "mock-model-v1"
    assert call.system_instruction == (
        "Answer the user's request directly and accurately."
    )


def test_mock_provider_consumes_actions() -> None:
    provider = ScriptedMockProvider(
        actions=[
            ProviderResponse(
                text="first"
            ),
            ProviderResponse(
                text="second"
            ),
        ]
    )

    assert provider.remaining_action_count == 2

    first = provider.generate(
        request=_request(),
        configuration=_configuration(),
    )

    assert first.text == "first"
    assert provider.remaining_action_count == 1

    second = provider.generate(
        request=_request(),
        configuration=_configuration(),
    )

    assert second.text == "second"
    assert provider.remaining_action_count == 0


def test_mock_provider_raises_scripted_provider_error() -> None:
    provider = ScriptedMockProvider(
        actions=[
            ProviderError(
                "provider failure"
            )
        ]
    )

    with pytest.raises(
        ProviderError,
        match="provider failure",
    ):
        provider.generate(
            request=_request(),
            configuration=_configuration(),
        )


def test_mock_provider_raises_scripted_timeout() -> None:
    provider = ScriptedMockProvider(
        actions=[
            ProviderTimeoutError(
                "timed out"
            )
        ]
    )

    with pytest.raises(
        ProviderTimeoutError,
        match="timed out",
    ):
        provider.generate(
            request=_request(),
            configuration=_configuration(),
        )


def test_mock_provider_raises_scripted_rate_limit() -> None:
    provider = ScriptedMockProvider(
        actions=[
            ProviderRateLimitError(
                "rate limited"
            )
        ]
    )

    with pytest.raises(
        ProviderRateLimitError,
        match="rate limited",
    ):
        provider.generate(
            request=_request(),
            configuration=_configuration(),
        )


def test_mock_provider_raises_scripted_invalid_response() -> None:
    provider = ScriptedMockProvider(
        actions=[
            ProviderInvalidResponseError(
                "invalid response"
            )
        ]
    )

    with pytest.raises(
        ProviderInvalidResponseError,
        match="invalid response",
    ):
        provider.generate(
            request=_request(),
            configuration=_configuration(),
        )


def test_mock_provider_records_failed_call() -> None:
    provider = ScriptedMockProvider(
        actions=[
            ProviderTimeoutError(
                "timed out"
            )
        ]
    )

    with pytest.raises(
        ProviderTimeoutError,
    ):
        provider.generate(
            request=_request(),
            configuration=_configuration(),
        )

    assert len(provider.calls) == 1


def test_mock_provider_rejects_configuration_for_other_provider() -> None:
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
        provider.generate(
            request=_request(),
            configuration=_configuration(
                provider="different-provider"
            ),
        )

    assert len(provider.calls) == 0
    assert provider.remaining_action_count == 1


def test_mock_provider_rejects_blank_provider_name() -> None:
    with pytest.raises(
        ValueError,
        match="provider_name must be non-blank",
    ):
        ScriptedMockProvider(
            provider_name="   ",
            actions=[],
        )


def test_mock_provider_reports_exhausted_script() -> None:
    provider = ScriptedMockProvider(
        actions=[]
    )

    with pytest.raises(
        RuntimeError,
        match="Mock provider script is exhausted",
    ):
        provider.generate(
            request=_request(),
            configuration=_configuration(),
        )

    assert len(provider.calls) == 1