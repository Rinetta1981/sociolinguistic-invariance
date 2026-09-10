from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from sociolinguistic_invariance.evaluation import (
    EvaluationRequest,
    ModelConfiguration,
    ProviderUsage,
)


class ProviderError(RuntimeError):
    """Base error raised by a model-provider adapter."""


class ProviderTimeoutError(ProviderError):
    """The provider request exceeded its allowed time."""


class ProviderRateLimitError(ProviderError):
    """The provider rejected the request because of rate limiting."""


class ProviderInvalidResponseError(ProviderError):
    """The provider returned a response that could not be interpreted."""


@dataclass(frozen=True, slots=True)
class ProviderResponse:
    """Provider-neutral successful model response."""

    text: str
    provider_request_id: str | None = None
    usage: ProviderUsage | None = None

    def __post_init__(self) -> None:
        """Validate provider response metadata."""

        if (
            self.provider_request_id is not None
            and not self.provider_request_id.strip()
        ):
            raise ValueError(
                "provider_request_id must be non-blank when provided."
            )


@dataclass(frozen=True, slots=True)
class MockProviderCall:
    """One call observed by the scripted mock provider."""

    request_id: str
    prompt_text: str
    requested_model: str
    system_instruction: str | None


@runtime_checkable
class ModelProvider(Protocol):
    """Provider-neutral interface used by the evaluation executor."""

    @property
    def provider_name(self) -> str:
        """Return the provider identifier."""

        ...

    def generate(
        self,
        *,
        request: EvaluationRequest,
        configuration: ModelConfiguration,
    ) -> ProviderResponse:
        """Generate one response for one evaluation request."""

        ...


ProviderAction = (
    ProviderResponse
    | ProviderError
)


class ScriptedMockProvider:
    """Deterministic provider used for execution tests.

    Each call consumes exactly one scripted action. An action is either
    a successful ProviderResponse or a ProviderError that will be raised.
    No network or external API is used.
    """

    def __init__(
        self,
        *,
        actions: Sequence[ProviderAction],
        provider_name: str = "mock",
    ) -> None:
        if not provider_name.strip():
            raise ValueError(
                "provider_name must be non-blank."
            )

        self._provider_name = provider_name
        self._actions: list[ProviderAction] = list(
            actions
        )
        self._calls: list[MockProviderCall] = []

    @property
    def provider_name(self) -> str:
        """Return the mock provider identifier."""

        return self._provider_name

    @property
    def calls(self) -> tuple[MockProviderCall, ...]:
        """Return an immutable record of observed calls."""

        return tuple(
            self._calls
        )

    @property
    def remaining_action_count(self) -> int:
        """Return the number of unused scripted actions."""

        return len(
            self._actions
        )

    def generate(
        self,
        *,
        request: EvaluationRequest,
        configuration: ModelConfiguration,
    ) -> ProviderResponse:
        """Consume and execute the next scripted action."""

        if configuration.provider != self.provider_name:
            raise ValueError(
                "Model configuration provider does not "
                "match provider adapter."
            )

        self._calls.append(
            MockProviderCall(
                request_id=request.request_id,
                prompt_text=request.prompt_text,
                requested_model=(
                    configuration.requested_model
                ),
                system_instruction=(
                    configuration.system_instruction
                ),
            )
        )

        if not self._actions:
            raise RuntimeError(
                "Mock provider script is exhausted."
            )

        action = self._actions.pop(
            0
        )

        if isinstance(
            action,
            ProviderError,
        ):
            raise action

        return action