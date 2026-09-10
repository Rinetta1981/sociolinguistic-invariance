import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Final
from uuid import uuid4

from sociolinguistic_invariance.core import TaskType, VariationCondition

EVALUATION_PROTOCOL_VERSION: Final = "evaluation-protocol-v0.1"

DEFAULT_SYSTEM_INSTRUCTION: Final = (
    "Answer the user's request directly and accurately."
)


class ResponseStatus(StrEnum):
    """Execution status for one model request."""

    SUCCESS = "SUCCESS"
    PROVIDER_ERROR = "PROVIDER_ERROR"
    TIMEOUT = "TIMEOUT"
    RATE_LIMITED = "RATE_LIMITED"
    INVALID_RESPONSE = "INVALID_RESPONSE"
    SKIPPED = "SKIPPED"


@dataclass(frozen=True, slots=True)
class ModelConfiguration:
    """Provider-neutral model configuration requested for one run."""

    provider: str
    requested_model: str
    temperature: float | None = 0.0
    top_p: float | None = None
    max_output_tokens: int | None = 512
    seed: int | None = None
    system_instruction: str | None = DEFAULT_SYSTEM_INSTRUCTION
    sdk_version: str | None = None

    def __post_init__(self) -> None:
        """Validate model configuration fields."""

        _require_nonblank(
            self.provider,
            field_name="provider",
        )
        _require_nonblank(
            self.requested_model,
            field_name="requested_model",
        )

        if self.temperature is not None and self.temperature < 0:
            raise ValueError(
                "temperature must be non-negative when provided."
            )

        if self.top_p is not None and not 0 <= self.top_p <= 1:
            raise ValueError(
                "top_p must be between 0 and 1 when provided."
            )

        if (
            self.max_output_tokens is not None
            and self.max_output_tokens <= 0
        ):
            raise ValueError(
                "max_output_tokens must be positive when provided."
            )

        if (
            self.system_instruction is not None
            and not self.system_instruction.strip()
        ):
            raise ValueError(
                "system_instruction must be non-blank when provided."
            )

        if (
            self.sdk_version is not None
            and not self.sdk_version.strip()
        ):
            raise ValueError(
                "sdk_version must be non-blank when provided."
            )


@dataclass(frozen=True, slots=True)
class EvaluationRun:
    """Metadata describing one evaluation run."""

    run_id: str
    artifact_id: str
    artifact_path: str
    artifact_sha256: str
    model_configuration: ModelConfiguration
    started_at: datetime
    git_commit: str | None = None
    evaluation_protocol_version: str = EVALUATION_PROTOCOL_VERSION

    def __post_init__(self) -> None:
        """Validate run metadata."""

        _require_nonblank(
            self.run_id,
            field_name="run_id",
        )
        _require_nonblank(
            self.artifact_id,
            field_name="artifact_id",
        )
        _require_nonblank(
            self.artifact_path,
            field_name="artifact_path",
        )
        _validate_sha256(
            self.artifact_sha256,
            field_name="artifact_sha256",
        )
        _validate_aware_datetime(
            self.started_at,
            field_name="started_at",
        )
        _require_nonblank(
            self.evaluation_protocol_version,
            field_name="evaluation_protocol_version",
        )

        if (
            self.git_commit is not None
            and not self.git_commit.strip()
        ):
            raise ValueError(
                "git_commit must be non-blank when provided."
            )


@dataclass(frozen=True, slots=True)
class EvaluationRequest:
    """One exact frozen prompt submission within an evaluation run."""

    run_id: str
    request_id: str
    family_id: str
    task_type: TaskType
    condition: VariationCondition
    prompt_text: str
    prompt_sha256: str
    order_index: int

    def __post_init__(self) -> None:
        """Validate request identity and prompt integrity."""

        _require_nonblank(
            self.run_id,
            field_name="run_id",
        )
        _require_nonblank(
            self.request_id,
            field_name="request_id",
        )
        _require_nonblank(
            self.family_id,
            field_name="family_id",
        )
        _require_nonblank(
            self.prompt_text,
            field_name="prompt_text",
        )
        _validate_sha256(
            self.prompt_sha256,
            field_name="prompt_sha256",
        )

        if self.order_index < 0:
            raise ValueError(
                "order_index must be non-negative."
            )

        expected_hash = sha256_text(self.prompt_text)

        if self.prompt_sha256 != expected_hash:
            raise ValueError(
                "prompt_sha256 does not match prompt_text. "
                f"Expected {expected_hash}; "
                f"found {self.prompt_sha256}."
            )


@dataclass(frozen=True, slots=True)
class ProviderUsage:
    """Token usage returned by a model provider when available."""

    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None

    def __post_init__(self) -> None:
        """Require token counts to be non-negative when present."""

        for field_name, token_count in (
            ("input_tokens", self.input_tokens),
            ("output_tokens", self.output_tokens),
            ("total_tokens", self.total_tokens),
        ):
            if token_count is not None and token_count < 0:
                raise ValueError(
                    f"{field_name} must be non-negative when provided."
                )


@dataclass(frozen=True, slots=True)
class AttemptRecord:
    """Execution evidence for one provider-call attempt."""

    attempt_number: int
    status: ResponseStatus
    started_at: datetime
    finished_at: datetime
    latency_seconds: float
    provider_request_id: str | None = None
    error_type: str | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        """Validate one provider attempt."""

        if self.attempt_number < 1:
            raise ValueError(
                "attempt_number must be at least 1."
            )

        _validate_aware_datetime(
            self.started_at,
            field_name="started_at",
        )
        _validate_aware_datetime(
            self.finished_at,
            field_name="finished_at",
        )

        if self.finished_at < self.started_at:
            raise ValueError(
                "finished_at must not precede started_at."
            )

        if self.latency_seconds < 0:
            raise ValueError(
                "latency_seconds must be non-negative."
            )

        for field_name, optional_value in (
            ("provider_request_id", self.provider_request_id),
            ("error_type", self.error_type),
            ("error_message", self.error_message),
        ):
            if (
                optional_value is not None
                and not optional_value.strip()
            ):
                raise ValueError(
                    f"{field_name} must be non-blank when provided."
                )


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    """Final provider-neutral result for one evaluation request."""

    run_id: str
    request_id: str
    family_id: str
    task_type: TaskType
    condition: VariationCondition
    provider: str
    requested_model: str
    prompt_sha256: str
    status: ResponseStatus
    request_started_at: datetime
    response_finished_at: datetime
    latency_seconds: float
    attempts: tuple[AttemptRecord, ...]
    response_text: str | None = None
    returned_model: str | None = None
    provider_request_id: str | None = None
    finish_reason: str | None = None
    usage: ProviderUsage | None = None
    error_type: str | None = None
    error_message: str | None = None
    evaluation_protocol_version: str = EVALUATION_PROTOCOL_VERSION

    def __post_init__(self) -> None:
        """Validate the final result and its attempt history."""

        for field_name, required_value in (
            ("run_id", self.run_id),
            ("request_id", self.request_id),
            ("family_id", self.family_id),
            ("provider", self.provider),
            ("requested_model", self.requested_model),
            (
                "evaluation_protocol_version",
                self.evaluation_protocol_version,
            ),
        ):
            _require_nonblank(
                required_value,
                field_name=field_name,
            )

        _validate_sha256(
            self.prompt_sha256,
            field_name="prompt_sha256",
        )
        _validate_aware_datetime(
            self.request_started_at,
            field_name="request_started_at",
        )
        _validate_aware_datetime(
            self.response_finished_at,
            field_name="response_finished_at",
        )

        if self.response_finished_at < self.request_started_at:
            raise ValueError(
                "response_finished_at must not precede "
                "request_started_at."
            )

        if self.latency_seconds < 0:
            raise ValueError(
                "latency_seconds must be non-negative."
            )

        if self.status is ResponseStatus.SKIPPED:
            if self.attempts:
                raise ValueError(
                    "A SKIPPED result must not contain provider attempts."
                )
        else:
            if not self.attempts:
                raise ValueError(
                    "A non-SKIPPED result must contain at least one attempt."
                )

            expected_numbers = tuple(
                range(
                    1,
                    len(self.attempts) + 1,
                )
            )

            actual_numbers = tuple(
                attempt.attempt_number
                for attempt in self.attempts
            )

            if actual_numbers != expected_numbers:
                raise ValueError(
                    "Attempt numbers must be contiguous and begin at 1."
                )

            if self.attempts[-1].status is not self.status:
                raise ValueError(
                    "Final attempt status must match result status."
                )

        if self.status is ResponseStatus.SUCCESS:
            if (
                self.response_text is None
                or not self.response_text.strip()
            ):
                raise ValueError(
                    "SUCCESS requires a non-blank response_text."
                )

        for field_name, optional_value in (
            ("response_text", self.response_text),
            ("returned_model", self.returned_model),
            ("provider_request_id", self.provider_request_id),
            ("finish_reason", self.finish_reason),
            ("error_type", self.error_type),
            ("error_message", self.error_message),
        ):
            if (
                optional_value is not None
                and not optional_value.strip()
            ):
                raise ValueError(
                    f"{field_name} must be non-blank when provided."
                )

    @property
    def retry_count(self) -> int:
        """Return the number of retries after the initial attempt."""

        if not self.attempts:
            return 0

        return len(self.attempts) - 1


def _require_nonblank(
    value: str,
    *,
    field_name: str,
) -> None:
    """Require a string to contain non-whitespace content."""

    if not value.strip():
        raise ValueError(
            f"{field_name} must be non-blank."
        )


def _validate_aware_datetime(
    value: datetime,
    *,
    field_name: str,
) -> None:
    """Require a timezone-aware datetime."""

    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(
            f"{field_name} must be timezone-aware."
        )


def _validate_sha256(
    value: str,
    *,
    field_name: str,
) -> None:
    """Require a lowercase 64-character SHA-256 hexadecimal digest."""

    if len(value) != 64:
        raise ValueError(
            f"{field_name} must contain exactly 64 hexadecimal characters."
        )

    if any(
        character not in "0123456789abcdef"
        for character in value
    ):
        raise ValueError(
            f"{field_name} must be lowercase hexadecimal."
        )


def sha256_text(text: str) -> str:
    """Return the SHA-256 digest of exact UTF-8 text."""

    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()


def new_run_id() -> str:
    """Create a collision-resistant run identifier."""

    return f"run_{uuid4().hex}"


def new_request_id() -> str:
    """Create a collision-resistant request identifier."""

    return f"req_{uuid4().hex}"


def utc_now() -> datetime:
    """Return the current timezone-aware UTC time."""

    return datetime.now(UTC)


def build_evaluation_request(
    *,
    run_id: str,
    family_id: str,
    task_type: TaskType,
    condition: VariationCondition,
    prompt_text: str,
    order_index: int,
) -> EvaluationRequest:
    """Construct one request and hash its exact prompt text."""

    return EvaluationRequest(
        run_id=run_id,
        request_id=new_request_id(),
        family_id=family_id,
        task_type=task_type,
        condition=condition,
        prompt_text=prompt_text,
        prompt_sha256=sha256_text(prompt_text),
        order_index=order_index,
    )


def _datetime_to_utc_string(value: datetime) -> str:
    """Serialize a timezone-aware datetime in UTC with a Z suffix."""

    _validate_aware_datetime(
        value,
        field_name="datetime",
    )

    return (
        value.astimezone(UTC)
        .isoformat()
        .replace("+00:00", "Z")
    )


def model_configuration_to_dict(
    configuration: ModelConfiguration,
) -> dict[str, object]:
    """Serialize provider-neutral model configuration."""

    return {
        "provider": configuration.provider,
        "requested_model": configuration.requested_model,
        "temperature": configuration.temperature,
        "top_p": configuration.top_p,
        "max_output_tokens": configuration.max_output_tokens,
        "seed": configuration.seed,
        "system_instruction": configuration.system_instruction,
        "sdk_version": configuration.sdk_version,
    }


def evaluation_run_to_dict(
    run: EvaluationRun,
) -> dict[str, object]:
    """Serialize evaluation-run metadata."""

    return {
        "run_id": run.run_id,
        "artifact_id": run.artifact_id,
        "artifact_path": run.artifact_path,
        "artifact_sha256": run.artifact_sha256,
        "model_configuration": model_configuration_to_dict(
            run.model_configuration
        ),
        "started_at": _datetime_to_utc_string(
            run.started_at
        ),
        "git_commit": run.git_commit,
        "evaluation_protocol_version": (
            run.evaluation_protocol_version
        ),
    }


def evaluation_request_to_dict(
    request: EvaluationRequest,
) -> dict[str, object]:
    """Serialize one exact evaluation request."""

    return {
        "run_id": request.run_id,
        "request_id": request.request_id,
        "family_id": request.family_id,
        "task_type": request.task_type.value,
        "condition": request.condition.value,
        "prompt_text": request.prompt_text,
        "prompt_sha256": request.prompt_sha256,
        "order_index": request.order_index,
    }


def provider_usage_to_dict(
    usage: ProviderUsage,
) -> dict[str, object]:
    """Serialize provider usage metadata."""

    return {
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "total_tokens": usage.total_tokens,
    }


def attempt_record_to_dict(
    attempt: AttemptRecord,
) -> dict[str, object]:
    """Serialize one provider attempt."""

    return {
        "attempt_number": attempt.attempt_number,
        "status": attempt.status.value,
        "started_at": _datetime_to_utc_string(
            attempt.started_at
        ),
        "finished_at": _datetime_to_utc_string(
            attempt.finished_at
        ),
        "latency_seconds": attempt.latency_seconds,
        "provider_request_id": attempt.provider_request_id,
        "error_type": attempt.error_type,
        "error_message": attempt.error_message,
    }


def evaluation_result_to_dict(
    result: EvaluationResult,
) -> dict[str, object]:
    """Serialize a completed provider-neutral evaluation result."""

    usage_payload: dict[str, object] | None = None

    if result.usage is not None:
        usage_payload = provider_usage_to_dict(
            result.usage
        )

    return {
        "run_id": result.run_id,
        "request_id": result.request_id,
        "family_id": result.family_id,
        "task_type": result.task_type.value,
        "condition": result.condition.value,
        "provider": result.provider,
        "requested_model": result.requested_model,
        "returned_model": result.returned_model,
        "prompt_sha256": result.prompt_sha256,
        "status": result.status.value,
        "response_text": result.response_text,
        "request_started_at": _datetime_to_utc_string(
            result.request_started_at
        ),
        "response_finished_at": _datetime_to_utc_string(
            result.response_finished_at
        ),
        "latency_seconds": result.latency_seconds,
        "retry_count": result.retry_count,
        "attempts": [
            attempt_record_to_dict(attempt)
            for attempt in result.attempts
        ],
        "provider_request_id": result.provider_request_id,
        "finish_reason": result.finish_reason,
        "usage": usage_payload,
        "error_type": result.error_type,
        "error_message": result.error_message,
        "evaluation_protocol_version": (
            result.evaluation_protocol_version
        ),
    }