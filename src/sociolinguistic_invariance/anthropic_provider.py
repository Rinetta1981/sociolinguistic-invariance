import anthropic
from anthropic.types import MessageParam

from sociolinguistic_invariance.evaluation import (
    EvaluationRequest,
    ModelConfiguration,
    ProviderUsage,
)
from sociolinguistic_invariance.provider import (
    ProviderConnectionError,
    ProviderError,
    ProviderInvalidResponseError,
    ProviderRateLimitError,
    ProviderResponse,
    ProviderTimeoutError,
)


def _error_message(
    error: BaseException,
) -> str:
    """Return a non-blank provider error message."""

    message = str(
        error
    ).strip()

    if message:
        return message

    return type(
        error
    ).__name__


def _extract_text(
    content: object,
) -> str:
    """Extract text blocks from an Anthropic message response."""

    if not isinstance(
        content,
        list,
    ):
        raise ProviderInvalidResponseError(
            "Anthropic response content was not a list."
        )

    text_parts: list[str] = []

    for block in content:
        block_type = getattr(
            block,
            "type",
            None,
        )

        if block_type != "text":
            continue

        text = getattr(
            block,
            "text",
            None,
        )

        if not isinstance(
            text,
            str,
        ):
            raise ProviderInvalidResponseError(
                "Anthropic text block did not contain "
                "string text."
            )

        text_parts.append(
            text
        )

    if not text_parts:
        raise ProviderInvalidResponseError(
            "Anthropic response contained no text blocks."
        )

    return "".join(
        text_parts
    )


class AnthropicProvider:
    """Anthropic Messages API adapter.

    SDK-level automatic retries are disabled when the provider is
    constructed through from_environment(). Retry behavior belongs to
    the provider-neutral evaluation executor.
    """

    def __init__(
        self,
        *,
        client: anthropic.Anthropic,
    ) -> None:
        self._client = client

    @classmethod
    def from_environment(
        cls,
    ) -> "AnthropicProvider":
        """Create a provider using ANTHROPIC_API_KEY."""

        client = anthropic.Anthropic(
            max_retries=0,
        )

        return cls(
            client=client
        )

    @property
    def provider_name(self) -> str:
        """Return the provider identifier."""

        return "anthropic"

    def generate(
        self,
        *,
        request: EvaluationRequest,
        configuration: ModelConfiguration,
    ) -> ProviderResponse:
        """Generate one provider-neutral response."""

        if (
            configuration.provider
            != self.provider_name
        ):
            raise ValueError(
                "Model configuration provider does not "
                "match Anthropic provider adapter."
            )

        if configuration.max_output_tokens is None:
            raise ValueError(
                "Anthropic execution requires "
                "max_output_tokens."
            )

        if configuration.temperature is not None:
            raise ValueError(
                "This Anthropic adapter requires "
                "temperature=None because the installed "
                "SDK interface does not expose temperature."
            )

        if configuration.top_p is not None:
            raise ValueError(
                "This Anthropic adapter requires top_p=None."
            )

        if configuration.seed is not None:
            raise ValueError(
                "This Anthropic adapter requires seed=None."
            )

        messages: list[MessageParam] = [
            {
                "role": "user",
                "content": request.prompt_text,
            }
        ]

        try:
            if (
                configuration.system_instruction
                is None
            ):
                message = (
                    self._client.messages.create(
                        model=(
                            configuration.requested_model
                        ),
                        max_tokens=(
                            configuration.max_output_tokens
                        ),
                        messages=messages,
                    )
                )

            else:
                message = (
                    self._client.messages.create(
                        model=(
                            configuration.requested_model
                        ),
                        max_tokens=(
                            configuration.max_output_tokens
                        ),
                        messages=messages,
                        system=(
                            configuration.system_instruction
                        ),
                    )
                )

        except anthropic.RateLimitError as error:
            raise ProviderRateLimitError(
                _error_message(
                    error
                )
            ) from error

        except anthropic.APITimeoutError as error:
            raise ProviderTimeoutError(
                _error_message(
                    error
                )
            ) from error

        except anthropic.APIConnectionError as error:
            raise ProviderConnectionError(
                _error_message(
                    error
                )
            ) from error

        except anthropic.APIStatusError as error:
            raise ProviderError(
                _error_message(
                    error
                )
            ) from error

        response_text = _extract_text(
            message.content
        )

        usage = ProviderUsage(
            input_tokens=(
                message.usage.input_tokens
            ),
            output_tokens=(
                message.usage.output_tokens
            ),
            total_tokens=(
                message.usage.input_tokens
                + message.usage.output_tokens
            ),
        )

        returned_model = str(
            message.model
        )

        finish_reason = (
            None
            if message.stop_reason is None
            else str(
                message.stop_reason
            )
        )

        return ProviderResponse(
            text=response_text,
            provider_request_id=(
                message._request_id
            ),
            usage=usage,
            returned_model=returned_model,
            finish_reason=finish_reason,
        )