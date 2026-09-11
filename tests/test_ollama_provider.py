from typing import Any

import pytest

from sociolinguistic_invariance.core import (
    TaskType,
    VariationCondition,
)
from sociolinguistic_invariance.evaluation import (
    EvaluationRequest,
    ModelConfiguration,
    sha256_text,
)
from sociolinguistic_invariance.ollama_provider import (
    OllamaProvider,
)
from sociolinguistic_invariance.provider import (
    ProviderError,
    ProviderInvalidResponseError,
)

PROMPT_TEXT = (
    "Η Μαδρίτη είναι η πρωτεύουσα "
    "της Πορτογαλίας. Γιατί;"
)


class RecordingTransport:
    """Record one local Ollama transport call."""

    def __init__(
        self,
        response: object,
    ) -> None:
        self.response = response

        self.calls: list[
            tuple[
                str,
                dict[str, object],
                float,
            ]
        ] = []

    def __call__(
        self,
        url: str,
        payload: dict[str, object],
        timeout_seconds: float,
    ) -> object:
        self.calls.append(
            (
                url,
                payload,
                timeout_seconds,
            )
        )

        return self.response


def _request() -> EvaluationRequest:
    """Create one evaluation request."""

    return EvaluationRequest(
        run_id="run_ollama_test",
        request_id="req_ollama_test",
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
    provider: str = "ollama",
    temperature: float | None = 0.0,
    top_p: float | None = None,
    max_output_tokens: int | None = 128,
    seed: int | None = 20260911,
    system_instruction: str | None = (
        "Answer the user's request directly "
        "and accurately."
    ),
) -> ModelConfiguration:
    """Create an Ollama model configuration."""

    return ModelConfiguration(
        provider=provider,
        requested_model="gemma3:4b",
        temperature=temperature,
        top_p=top_p,
        max_output_tokens=max_output_tokens,
        seed=seed,
        system_instruction=system_instruction,
        sdk_version=None,
    )


def _successful_response() -> dict[str, Any]:
    """Create one Ollama-like response."""

    return {
        "model": "gemma3:4b",
        "response": (
            "Η Μαδρίτη είναι η πρωτεύουσα "
            "της Ισπανίας."
        ),
        "done": True,
        "done_reason": "stop",
        "prompt_eval_count": 24,
        "eval_count": 12,
    }


def _provider(
    response: object,
) -> tuple[
    RecordingTransport,
    OllamaProvider,
]:
    """Create one provider with fake transport."""

    transport = RecordingTransport(
        response
    )

    provider = OllamaProvider(
        transport=transport
    )

    return (
        transport,
        provider,
    )


def test_provider_name_is_ollama() -> None:
    _, provider = _provider(
        _successful_response()
    )

    assert provider.provider_name == (
        "ollama"
    )


def test_default_base_url_is_local() -> None:
    _, provider = _provider(
        _successful_response()
    )

    assert provider.base_url == (
        "http://localhost:11434"
    )


def test_generate_uses_local_generate_endpoint() -> None:
    transport, provider = _provider(
        _successful_response()
    )

    provider.generate(
        request=_request(),
        configuration=_configuration(),
    )

    assert len(
        transport.calls
    ) == 1

    assert transport.calls[
        0
    ][0] == (
        "http://localhost:11434"
        "/api/generate"
    )


def test_generate_preserves_exact_prompt() -> None:
    transport, provider = _provider(
        _successful_response()
    )

    provider.generate(
        request=_request(),
        configuration=_configuration(),
    )

    payload = transport.calls[
        0
    ][1]

    assert payload[
        "prompt"
    ] == PROMPT_TEXT


def test_generate_sends_expected_payload() -> None:
    transport, provider = _provider(
        _successful_response()
    )

    provider.generate(
        request=_request(),
        configuration=_configuration(),
    )

    payload = transport.calls[
        0
    ][1]

    assert payload == {
        "model": "gemma3:4b",
        "prompt": PROMPT_TEXT,
        "stream": False,
        "system": (
            "Answer the user's request "
            "directly and accurately."
        ),
        "options": {
            "num_predict": 128,
            "temperature": 0.0,
            "seed": 20260911,
        },
    }


def test_generate_can_send_top_p() -> None:
    transport, provider = _provider(
        _successful_response()
    )

    provider.generate(
        request=_request(),
        configuration=_configuration(
            top_p=0.9
        ),
    )

    payload = transport.calls[
        0
    ][1]

    options = payload[
        "options"
    ]

    assert isinstance(
        options,
        dict,
    )

    assert options[
        "top_p"
    ] == 0.9


def test_generate_omits_system_when_none() -> None:
    transport, provider = _provider(
        _successful_response()
    )

    provider.generate(
        request=_request(),
        configuration=_configuration(
            system_instruction=None
        ),
    )

    payload = transport.calls[
        0
    ][1]

    assert "system" not in payload


def test_generate_can_omit_options() -> None:
    transport, provider = _provider(
        _successful_response()
    )

    provider.generate(
        request=_request(),
        configuration=_configuration(
            temperature=None,
            top_p=None,
            max_output_tokens=None,
            seed=None,
        ),
    )

    payload = transport.calls[
        0
    ][1]

    assert "options" not in payload


def test_generate_preserves_response_text() -> None:
    _, provider = _provider(
        _successful_response()
    )

    response = provider.generate(
        request=_request(),
        configuration=_configuration(),
    )

    assert response.text == (
        "Η Μαδρίτη είναι η πρωτεύουσα "
        "της Ισπανίας."
    )


def test_generate_preserves_model_and_finish_reason() -> None:
    _, provider = _provider(
        _successful_response()
    )

    response = provider.generate(
        request=_request(),
        configuration=_configuration(),
    )

    assert response.returned_model == (
        "gemma3:4b"
    )

    assert response.finish_reason == (
        "stop"
    )


def test_generate_preserves_token_usage() -> None:
    _, provider = _provider(
        _successful_response()
    )

    response = provider.generate(
        request=_request(),
        configuration=_configuration(),
    )

    assert response.usage is not None

    assert response.usage.input_tokens == 24

    assert response.usage.output_tokens == 12

    assert response.usage.total_tokens == 36


def test_generate_allows_missing_usage() -> None:
    raw_response = (
        _successful_response()
    )

    del raw_response[
        "prompt_eval_count"
    ]

    del raw_response[
        "eval_count"
    ]

    _, provider = _provider(
        raw_response
    )

    response = provider.generate(
        request=_request(),
        configuration=_configuration(),
    )

    assert response.usage is None


def test_generate_allows_blank_text_for_executor_validation() -> None:
    raw_response = (
        _successful_response()
    )

    raw_response[
        "response"
    ] = "   "

    _, provider = _provider(
        raw_response
    )

    response = provider.generate(
        request=_request(),
        configuration=_configuration(),
    )

    assert response.text == "   "


def test_generate_rejects_provider_mismatch() -> None:
    _, provider = _provider(
        _successful_response()
    )

    with pytest.raises(
        ValueError,
        match=(
            "Model configuration provider "
            "does not match Ollama "
            "provider adapter"
        ),
    ):
        provider.generate(
            request=_request(),
            configuration=_configuration(
                provider="different-provider"
            ),
        )


def test_generate_rejects_non_object_response() -> None:
    _, provider = _provider(
        ["not", "an", "object"]
    )

    with pytest.raises(
        ProviderInvalidResponseError,
        match=(
            "Ollama response was not "
            "a JSON object"
        ),
    ):
        provider.generate(
            request=_request(),
            configuration=_configuration(),
        )


def test_generate_rejects_missing_response_text() -> None:
    raw_response = (
        _successful_response()
    )

    del raw_response[
        "response"
    ]

    _, provider = _provider(
        raw_response
    )

    with pytest.raises(
        ProviderInvalidResponseError,
        match=(
            "did not contain string "
            "response text"
        ),
    ):
        provider.generate(
            request=_request(),
            configuration=_configuration(),
        )


def test_generate_rejects_incomplete_response() -> None:
    raw_response = (
        _successful_response()
    )

    raw_response[
        "done"
    ] = False

    _, provider = _provider(
        raw_response
    )

    with pytest.raises(
        ProviderInvalidResponseError,
        match="done=true",
    ):
        provider.generate(
            request=_request(),
            configuration=_configuration(),
        )


def test_generate_maps_response_error() -> None:
    _, provider = _provider(
        {
            "error": (
                "model not found"
            )
        }
    )

    with pytest.raises(
        ProviderError,
        match="model not found",
    ):
        provider.generate(
            request=_request(),
            configuration=_configuration(),
        )


def test_generate_rejects_invalid_token_count() -> None:
    raw_response = (
        _successful_response()
    )

    raw_response[
        "eval_count"
    ] = "twelve"

    _, provider = _provider(
        raw_response
    )

    with pytest.raises(
        ProviderInvalidResponseError,
        match="eval_count",
    ):
        provider.generate(
            request=_request(),
            configuration=_configuration(),
        )


def test_provider_rejects_nonlocal_server() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "only permits loopback "
            "addresses"
        ),
    ):
        OllamaProvider(
            base_url=(
                "https://example.com"
            )
        )


def test_provider_rejects_zero_timeout() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "timeout_seconds must be "
            "finite and positive"
        ),
    ):
        OllamaProvider(
            timeout_seconds=0.0
        )