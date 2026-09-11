from dataclasses import dataclass
from typing import Any, cast

import anthropic
import pytest

import sociolinguistic_invariance.anthropic_provider as anthropic_provider_module
from sociolinguistic_invariance.anthropic_provider import (
    AnthropicProvider,
)
from sociolinguistic_invariance.core import (
    TaskType,
    VariationCondition,
)
from sociolinguistic_invariance.evaluation import (
    EvaluationRequest,
    ModelConfiguration,
    sha256_text,
)
from sociolinguistic_invariance.provider import (
    ProviderConnectionError,
    ProviderError,
    ProviderInvalidResponseError,
    ProviderRateLimitError,
    ProviderTimeoutError,
)

PROMPT_TEXT = "Η Μαδρίτη είναι η πρωτεύουσα της Πορτογαλίας. Γιατί;"


@dataclass
class FakeTextBlock:
    """Minimal Anthropic-like text block."""

    text: object
    type: str = "text"


@dataclass
class FakeOtherBlock:
    """Minimal non-text Anthropic-like content block."""

    type: str = "tool_use"


@dataclass
class FakeUsage:
    """Minimal Anthropic-like usage object."""

    input_tokens: int
    output_tokens: int


@dataclass
class FakeMessage:
    """Minimal Anthropic-like message response."""

    content: object
    usage: FakeUsage
    model: str
    stop_reason: str | None
    _request_id: str | None


class FakeMessagesResource:
    """Record calls and return or raise one scripted action."""

    def __init__(
        self,
        action: object,
    ) -> None:
        self.action = action
        self.calls: list[dict[str, Any]] = []

    def create(
        self,
        **kwargs: Any,
    ) -> Any:
        self.calls.append(
            kwargs
        )

        if isinstance(
            self.action,
            BaseException,
        ):
            raise self.action

        return self.action


class FakeClient:
    """Minimal Anthropic-like client."""

    def __init__(
        self,
        action: object,
    ) -> None:
        self.messages = FakeMessagesResource(
            action
        )


class FakeRateLimitError(Exception):
    """Fake SDK rate-limit error."""


class FakeTimeoutError(Exception):
    """Fake SDK timeout error."""


class FakeConnectionError(Exception):
    """Fake SDK connection error."""


class FakeStatusError(Exception):
    """Fake SDK HTTP status error."""


def _request() -> EvaluationRequest:
    """Create one valid evaluation request."""

    return EvaluationRequest(
        run_id="run_anthropic_test",
        request_id="req_anthropic_test",
        family_id="FP_0001",
        task_type=(
            TaskType.FALSE_PREMISE_CORRECTION
        ),
        condition=VariationCondition.STANDARD,
        prompt_text=PROMPT_TEXT,
        prompt_sha256=sha256_text(
            PROMPT_TEXT
        ),
        order_index=0,
    )


def _configuration(
    *,
    provider: str = "anthropic",
    max_output_tokens: int | None = 256,
    temperature: float | None = None,
    top_p: float | None = None,
    seed: int | None = None,
    system_instruction: str | None = (
        "Answer directly and accurately."
    ),
) -> ModelConfiguration:
    """Create an Anthropic-compatible configuration."""

    return ModelConfiguration(
        provider=provider,
        requested_model="claude-test-model",
        temperature=temperature,
        top_p=top_p,
        max_output_tokens=max_output_tokens,
        seed=seed,
        system_instruction=system_instruction,
        sdk_version="1.5.0",
    )


def _message(
    *,
    content: object | None = None,
    stop_reason: str | None = "end_turn",
) -> FakeMessage:
    """Create one successful fake Anthropic response."""

    effective_content = (
        content
        if content is not None
        else [
            FakeTextBlock(
                text="Η Μαδρίτη είναι η πρωτεύουσα της Ισπανίας."
            )
        ]
    )

    return FakeMessage(
        content=effective_content,
        usage=FakeUsage(
            input_tokens=20,
            output_tokens=10,
        ),
        model="claude-returned-model",
        stop_reason=stop_reason,
        _request_id="req_provider_123",
    )


def _provider(
    action: object,
) -> tuple[
    FakeClient,
    AnthropicProvider,
]:
    """Create the adapter around a fake client."""

    fake_client = FakeClient(
        action
    )

    provider = AnthropicProvider(
        client=cast(
            anthropic.Anthropic,
            fake_client,
        )
    )

    return (
        fake_client,
        provider,
    )


def _install_fake_sdk_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Replace SDK error classes for deterministic tests."""

    monkeypatch.setattr(
        anthropic_provider_module.anthropic,
        "RateLimitError",
        FakeRateLimitError,
    )

    monkeypatch.setattr(
        anthropic_provider_module.anthropic,
        "APITimeoutError",
        FakeTimeoutError,
    )

    monkeypatch.setattr(
        anthropic_provider_module.anthropic,
        "APIConnectionError",
        FakeConnectionError,
    )

    monkeypatch.setattr(
        anthropic_provider_module.anthropic,
        "APIStatusError",
        FakeStatusError,
    )


def test_provider_name_is_anthropic() -> None:
    _, provider = _provider(
        _message()
    )

    assert provider.provider_name == (
        "anthropic"
    )


def test_generate_sends_expected_messages_request() -> None:
    fake_client, provider = _provider(
        _message()
    )

    response = provider.generate(
        request=_request(),
        configuration=_configuration(),
    )

    assert len(
        fake_client.messages.calls
    ) == 1

    assert fake_client.messages.calls[
        0
    ] == {
        "model": "claude-test-model",
        "max_tokens": 256,
        "messages": [
            {
                "role": "user",
                "content": PROMPT_TEXT,
            }
        ],
        "system": (
            "Answer directly and accurately."
        ),
    }

    assert response.text == (
        "Η Μαδρίτη είναι η πρωτεύουσα της Ισπανίας."
    )


def test_generate_does_not_send_unsupported_parameters() -> None:
    fake_client, provider = _provider(
        _message()
    )

    provider.generate(
        request=_request(),
        configuration=_configuration(),
    )

    sent = fake_client.messages.calls[
        0
    ]

    assert "temperature" not in sent
    assert "top_p" not in sent
    assert "seed" not in sent


def test_generate_omits_system_when_none() -> None:
    fake_client, provider = _provider(
        _message()
    )

    provider.generate(
        request=_request(),
        configuration=_configuration(
            system_instruction=None
        ),
    )

    sent = fake_client.messages.calls[
        0
    ]

    assert "system" not in sent


def test_generate_preserves_response_metadata() -> None:
    _, provider = _provider(
        _message()
    )

    response = provider.generate(
        request=_request(),
        configuration=_configuration(),
    )

    assert response.provider_request_id == (
        "req_provider_123"
    )

    assert response.returned_model == (
        "claude-returned-model"
    )

    assert response.finish_reason == (
        "end_turn"
    )

    assert response.usage is not None

    assert response.usage.input_tokens == 20
    assert response.usage.output_tokens == 10
    assert response.usage.total_tokens == 30


def test_generate_allows_missing_stop_reason() -> None:
    _, provider = _provider(
        _message(
            stop_reason=None
        )
    )

    response = provider.generate(
        request=_request(),
        configuration=_configuration(),
    )

    assert response.finish_reason is None


def test_generate_concatenates_text_blocks() -> None:
    content = [
        FakeTextBlock(
            text="Πρώτο "
        ),
        FakeOtherBlock(),
        FakeTextBlock(
            text="δεύτερο."
        ),
    ]

    _, provider = _provider(
        _message(
            content=content
        )
    )

    response = provider.generate(
        request=_request(),
        configuration=_configuration(),
    )

    assert response.text == (
        "Πρώτο δεύτερο."
    )


def test_generate_rejects_response_without_text_blocks() -> None:
    _, provider = _provider(
        _message(
            content=[
                FakeOtherBlock()
            ]
        )
    )

    with pytest.raises(
        ProviderInvalidResponseError,
        match=(
            "Anthropic response contained "
            "no text blocks"
        ),
    ):
        provider.generate(
            request=_request(),
            configuration=_configuration(),
        )


def test_generate_rejects_non_list_content() -> None:
    _, provider = _provider(
        _message(
            content="not a list"
        )
    )

    with pytest.raises(
        ProviderInvalidResponseError,
        match=(
            "Anthropic response content "
            "was not a list"
        ),
    ):
        provider.generate(
            request=_request(),
            configuration=_configuration(),
        )


def test_generate_rejects_non_string_text_block() -> None:
    _, provider = _provider(
        _message(
            content=[
                FakeTextBlock(
                    text=123
                )
            ]
        )
    )

    with pytest.raises(
        ProviderInvalidResponseError,
        match=(
            "Anthropic text block did not "
            "contain string text"
        ),
    ):
        provider.generate(
            request=_request(),
            configuration=_configuration(),
        )


def test_generate_rejects_provider_mismatch() -> None:
    _, provider = _provider(
        _message()
    )

    with pytest.raises(
        ValueError,
        match=(
            "Model configuration provider "
            "does not match Anthropic provider adapter"
        ),
    ):
        provider.generate(
            request=_request(),
            configuration=_configuration(
                provider="different-provider"
            ),
        )


def test_generate_requires_max_output_tokens() -> None:
    _, provider = _provider(
        _message()
    )

    with pytest.raises(
        ValueError,
        match=(
            "Anthropic execution requires "
            "max_output_tokens"
        ),
    ):
        provider.generate(
            request=_request(),
            configuration=_configuration(
                max_output_tokens=None
            ),
        )


def test_generate_rejects_temperature() -> None:
    _, provider = _provider(
        _message()
    )

    with pytest.raises(
        ValueError,
        match=(
            "temperature=None"
        ),
    ):
        provider.generate(
            request=_request(),
            configuration=_configuration(
                temperature=0.0
            ),
        )


def test_generate_rejects_top_p() -> None:
    _, provider = _provider(
        _message()
    )

    with pytest.raises(
        ValueError,
        match="top_p=None",
    ):
        provider.generate(
            request=_request(),
            configuration=_configuration(
                top_p=0.8
            ),
        )


def test_generate_rejects_seed() -> None:
    _, provider = _provider(
        _message()
    )

    with pytest.raises(
        ValueError,
        match="seed=None",
    ):
        provider.generate(
            request=_request(),
            configuration=_configuration(
                seed=42
            ),
        )


def test_rate_limit_maps_to_provider_rate_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_sdk_errors(
        monkeypatch
    )

    _, provider = _provider(
        FakeRateLimitError(
            "rate limited"
        )
    )

    with pytest.raises(
        ProviderRateLimitError,
        match="rate limited",
    ):
        provider.generate(
            request=_request(),
            configuration=_configuration(),
        )


def test_timeout_maps_to_provider_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_sdk_errors(
        monkeypatch
    )

    _, provider = _provider(
        FakeTimeoutError(
            "timed out"
        )
    )

    with pytest.raises(
        ProviderTimeoutError,
        match="timed out",
    ):
        provider.generate(
            request=_request(),
            configuration=_configuration(),
        )


def test_connection_failure_maps_to_provider_connection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_sdk_errors(
        monkeypatch
    )

    _, provider = _provider(
        FakeConnectionError(
            "connection failed"
        )
    )

    with pytest.raises(
        ProviderConnectionError,
        match="connection failed",
    ):
        provider.generate(
            request=_request(),
            configuration=_configuration(),
        )


def test_status_error_maps_to_generic_provider_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_sdk_errors(
        monkeypatch
    )

    _, provider = _provider(
        FakeStatusError(
            "HTTP failure"
        )
    )

    with pytest.raises(
        ProviderError,
        match="HTTP failure",
    ):
        provider.generate(
            request=_request(),
            configuration=_configuration(),
        )


def test_from_environment_disables_sdk_retries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_kwargs: dict[str, object] = {}

    fake_client = FakeClient(
        _message()
    )

    def fake_constructor(
        **kwargs: object,
    ) -> FakeClient:
        captured_kwargs.update(
            kwargs
        )

        return fake_client

    monkeypatch.setattr(
        anthropic_provider_module.anthropic,
        "Anthropic",
        fake_constructor,
    )

    provider = (
        AnthropicProvider.from_environment()
    )

    assert provider.provider_name == (
        "anthropic"
    )

    assert captured_kwargs == {
        "max_retries": 0
    }