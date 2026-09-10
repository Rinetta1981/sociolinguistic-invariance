import math
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Final

from sociolinguistic_invariance.evaluation import (
    AttemptRecord,
    EvaluationRequest,
    EvaluationResult,
    ModelConfiguration,
    ProviderUsage,
    ResponseStatus,
    utc_now,
)
from sociolinguistic_invariance.provider import (
    ModelProvider,
    ProviderError,
    ProviderInvalidResponseError,
    ProviderRateLimitError,
    ProviderTimeoutError,
)

RETRYABLE_STATUSES: Final[frozenset[ResponseStatus]] = frozenset(
    {
        ResponseStatus.TIMEOUT,
        ResponseStatus.RATE_LIMITED,
    }
)


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """Bounded retry policy for transient provider failures."""

    max_attempts: int = 3
    initial_backoff_seconds: float = 1.0
    backoff_multiplier: float = 2.0
    max_backoff_seconds: float = 8.0

    def __post_init__(self) -> None:
        """Validate retry-policy configuration."""

        if (
            isinstance(self.max_attempts, bool)
            or self.max_attempts < 1
        ):
            raise ValueError(
                "max_attempts must be a positive integer."
            )

        float_fields = (
            (
                "initial_backoff_seconds",
                self.initial_backoff_seconds,
            ),
            (
                "backoff_multiplier",
                self.backoff_multiplier,
            ),
            (
                "max_backoff_seconds",
                self.max_backoff_seconds,
            ),
        )

        for field_name, value in float_fields:
            if not math.isfinite(value):
                raise ValueError(
                    f"{field_name} must be finite."
                )

        if self.initial_backoff_seconds < 0:
            raise ValueError(
                "initial_backoff_seconds must be non-negative."
            )

        if self.backoff_multiplier < 1.0:
            raise ValueError(
                "backoff_multiplier must be at least 1.0."
            )

        if self.max_backoff_seconds < 0:
            raise ValueError(
                "max_backoff_seconds must be non-negative."
            )

        if (
            self.max_backoff_seconds
            < self.initial_backoff_seconds
        ):
            raise ValueError(
                "max_backoff_seconds must be greater than "
                "or equal to initial_backoff_seconds."
            )

    def backoff_seconds_after_failure(
        self,
        failed_attempt_number: int,
    ) -> float:
        """Return backoff before the next attempt."""

        if (
            isinstance(failed_attempt_number, bool)
            or failed_attempt_number < 1
        ):
            raise ValueError(
                "failed_attempt_number must be a positive integer."
            )

        uncapped_backoff = (
            self.initial_backoff_seconds
            * (
                self.backoff_multiplier
                ** (failed_attempt_number - 1)
            )
        )

        return min(
            uncapped_backoff,
            self.max_backoff_seconds,
        )


def _elapsed_seconds(
    *,
    started: float,
    finished: float,
) -> float:
    """Calculate elapsed monotonic time defensively."""

    elapsed = finished - started

    if elapsed < 0:
        raise RuntimeError(
            "Monotonic clock moved backwards."
        )

    return elapsed


def _status_for_provider_error(
    error: ProviderError,
) -> ResponseStatus:
    """Map provider-neutral exceptions to result statuses."""

    if isinstance(
        error,
        ProviderTimeoutError,
    ):
        return ResponseStatus.TIMEOUT

    if isinstance(
        error,
        ProviderRateLimitError,
    ):
        return ResponseStatus.RATE_LIMITED

    if isinstance(
        error,
        ProviderInvalidResponseError,
    ):
        return ResponseStatus.INVALID_RESPONSE

    return ResponseStatus.PROVIDER_ERROR


def _normalized_error_message(
    error: ProviderError,
) -> str:
    """Return a non-blank error message for audit records."""

    message = str(
        error
    ).strip()

    if message:
        return message

    return type(
        error
    ).__name__


class EvaluationExecutor:
    """Execute evaluation requests through a provider adapter."""

    def __init__(
        self,
        *,
        provider: ModelProvider,
        configuration: ModelConfiguration,
        retry_policy: RetryPolicy | None = None,
        now_fn: Callable[[], datetime] = utc_now,
        monotonic_fn: Callable[[], float] = time.perf_counter,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        if (
            provider.provider_name
            != configuration.provider
        ):
            raise ValueError(
                "Model configuration provider does not "
                "match provider adapter."
            )

        self._provider = provider
        self._configuration = configuration
        self._retry_policy = (
            retry_policy
            if retry_policy is not None
            else RetryPolicy()
        )
        self._now_fn = now_fn
        self._monotonic_fn = monotonic_fn
        self._sleep_fn = sleep_fn

    @property
    def provider(self) -> ModelProvider:
        """Return the configured provider adapter."""

        return self._provider

    @property
    def configuration(self) -> ModelConfiguration:
        """Return the immutable model configuration."""

        return self._configuration

    @property
    def retry_policy(self) -> RetryPolicy:
        """Return the retry policy."""

        return self._retry_policy

    def execute_request(
        self,
        request: EvaluationRequest,
    ) -> EvaluationResult:
        """Execute one request and preserve all attempts."""

        request_started_at = self._now_fn()
        request_started_monotonic = (
            self._monotonic_fn()
        )

        attempts: list[AttemptRecord] = []

        final_status = ResponseStatus.PROVIDER_ERROR
        final_response_text: str | None = None
        final_provider_request_id: str | None = None
        final_usage: ProviderUsage | None = None
        final_error_type: str | None = None
        final_error_message: str | None = None

        for attempt_number in range(
            1,
            self._retry_policy.max_attempts + 1,
        ):
            attempt_started_at = self._now_fn()
            attempt_started_monotonic = (
                self._monotonic_fn()
            )

            try:
                response = self._provider.generate(
                    request=request,
                    configuration=self._configuration,
                )

            except ProviderError as error:
                attempt_finished_monotonic = (
                    self._monotonic_fn()
                )
                attempt_finished_at = self._now_fn()

                status = _status_for_provider_error(
                    error
                )

                error_type = type(
                    error
                ).__name__

                error_message = (
                    _normalized_error_message(
                        error
                    )
                )

                attempts.append(
                    AttemptRecord(
                        attempt_number=attempt_number,
                        status=status,
                        started_at=attempt_started_at,
                        finished_at=attempt_finished_at,
                        latency_seconds=(
                            _elapsed_seconds(
                                started=(
                                    attempt_started_monotonic
                                ),
                                finished=(
                                    attempt_finished_monotonic
                                ),
                            )
                        ),
                        error_type=error_type,
                        error_message=error_message,
                    )
                )

                final_status = status
                final_response_text = None
                final_provider_request_id = None
                final_usage = None
                final_error_type = error_type
                final_error_message = error_message

                should_retry = (
                    status in RETRYABLE_STATUSES
                    and attempt_number
                    < self._retry_policy.max_attempts
                )

                if should_retry:
                    backoff_seconds = (
                        self._retry_policy
                        .backoff_seconds_after_failure(
                            attempt_number
                        )
                    )

                    self._sleep_fn(
                        backoff_seconds
                    )

                    continue

                break

            attempt_finished_monotonic = (
                self._monotonic_fn()
            )
            attempt_finished_at = self._now_fn()

            attempt_latency_seconds = (
                _elapsed_seconds(
                    started=(
                        attempt_started_monotonic
                    ),
                    finished=(
                        attempt_finished_monotonic
                    ),
                )
            )

            if not response.text.strip():
                error_type = (
                    "BlankProviderResponse"
                )
                error_message = (
                    "Provider returned blank response text."
                )

                attempts.append(
                    AttemptRecord(
                        attempt_number=attempt_number,
                        status=(
                            ResponseStatus.INVALID_RESPONSE
                        ),
                        started_at=attempt_started_at,
                        finished_at=attempt_finished_at,
                        latency_seconds=(
                            attempt_latency_seconds
                        ),
                        provider_request_id=(
                            response.provider_request_id
                        ),
                        error_type=error_type,
                        error_message=error_message,
                    )
                )

                final_status = (
                    ResponseStatus.INVALID_RESPONSE
                )
                final_response_text = None
                final_provider_request_id = (
                    response.provider_request_id
                )
                final_usage = response.usage
                final_error_type = error_type
                final_error_message = error_message

                break

            attempts.append(
                AttemptRecord(
                    attempt_number=attempt_number,
                    status=ResponseStatus.SUCCESS,
                    started_at=attempt_started_at,
                    finished_at=attempt_finished_at,
                    latency_seconds=(
                        attempt_latency_seconds
                    ),
                    provider_request_id=(
                        response.provider_request_id
                    ),
                )
            )

            final_status = ResponseStatus.SUCCESS
            final_response_text = response.text
            final_provider_request_id = (
                response.provider_request_id
            )
            final_usage = response.usage
            final_error_type = None
            final_error_message = None

            break

        if not attempts:
            raise RuntimeError(
                "Evaluation execution produced no attempts."
            )

        request_finished_monotonic = (
            self._monotonic_fn()
        )

        total_latency_seconds = (
            _elapsed_seconds(
                started=request_started_monotonic,
                finished=request_finished_monotonic,
            )
        )

        response_finished_at = (
            attempts[-1].finished_at
        )

        return EvaluationResult(
            run_id=request.run_id,
            request_id=request.request_id,
            family_id=request.family_id,
            task_type=request.task_type,
            condition=request.condition,
            provider=self._configuration.provider,
            requested_model=(
                self._configuration.requested_model
            ),
            prompt_sha256=request.prompt_sha256,
            status=final_status,
            request_started_at=request_started_at,
            response_finished_at=(
                response_finished_at
            ),
            latency_seconds=(
                total_latency_seconds
            ),
            attempts=tuple(
                attempts
            ),
            response_text=final_response_text,
            provider_request_id=(
                final_provider_request_id
            ),
            usage=final_usage,
            error_type=final_error_type,
            error_message=final_error_message,
        )