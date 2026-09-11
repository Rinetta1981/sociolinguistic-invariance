import json
import math
from collections.abc import Callable
from typing import Final
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from sociolinguistic_invariance.evaluation import (
    EvaluationRequest,
    ModelConfiguration,
    ProviderUsage,
)
from sociolinguistic_invariance.provider import (
    ProviderConnectionError,
    ProviderError,
    ProviderInvalidResponseError,
    ProviderResponse,
    ProviderTimeoutError,
)

DEFAULT_OLLAMA_BASE_URL: Final = (
    "http://localhost:11434"
)

DEFAULT_TIMEOUT_SECONDS: Final = 120.0

_LOOPBACK_HOSTS: Final = frozenset(
    {
        "localhost",
        "127.0.0.1",
        "::1",
    }
)

OllamaTransport = Callable[
    [
        str,
        dict[str, object],
        float,
    ],
    object,
]


def _error_message(
    error: BaseException,
) -> str:
    """Return a non-blank error message."""

    message = str(
        error
    ).strip()

    if message:
        return message

    return type(
        error
    ).__name__


def _http_error_message(
    error: HTTPError,
) -> str:
    """Extract useful detail from an Ollama HTTP error."""

    try:
        raw_body = error.read().decode(
            "utf-8",
            errors="replace",
        ).strip()
    except Exception:
        raw_body = ""

    if raw_body:
        try:
            decoded = json.loads(
                raw_body
            )
        except json.JSONDecodeError:
            return (
                f"Ollama HTTP {error.code}: "
                f"{raw_body}"
            )

        if isinstance(
            decoded,
            dict,
        ):
            provider_message = decoded.get(
                "error"
            )

            if isinstance(
                provider_message,
                str,
            ) and provider_message.strip():
                return (
                    f"Ollama HTTP {error.code}: "
                    f"{provider_message.strip()}"
                )

        return (
            f"Ollama HTTP {error.code}: "
            f"{raw_body}"
        )

    return (
        f"Ollama HTTP {error.code}: "
        f"{error.reason}"
    )


def _default_transport(
    url: str,
    payload: dict[str, object],
    timeout_seconds: float,
) -> object:
    """POST one JSON request to the local Ollama API."""

    request = Request(
        url=url,
        data=json.dumps(
            payload,
            ensure_ascii=False,
        ).encode(
            "utf-8"
        ),
        headers={
            "Content-Type": (
                "application/json"
            ),
        },
        method="POST",
    )

    try:
        with urlopen(
            request,
            timeout=timeout_seconds,
        ) as response:
            raw_response = response.read()

    except HTTPError as error:
        raise ProviderError(
            _http_error_message(
                error
            )
        ) from error

    except URLError as error:
        reason = error.reason

        if isinstance(
            reason,
            TimeoutError,
        ):
            raise ProviderTimeoutError(
                _error_message(
                    reason
                )
            ) from error

        raise ProviderConnectionError(
            _error_message(
                error
            )
        ) from error

    except TimeoutError as error:
        raise ProviderTimeoutError(
            _error_message(
                error
            )
        ) from error

    try:
        decoded = json.loads(
            raw_response.decode(
                "utf-8"
            )
        )
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as error:
        raise ProviderInvalidResponseError(
            "Ollama returned invalid JSON."
        ) from error

    return decoded


def _validate_base_url(
    base_url: str,
) -> str:
    """Validate that Ollama points only to this machine."""

    normalized = base_url.rstrip(
        "/"
    )

    if not normalized:
        raise ValueError(
            "Ollama base_url must be non-blank."
        )

    parsed = urlparse(
        normalized
    )

    if parsed.scheme not in {
        "http",
        "https",
    }:
        raise ValueError(
            "Ollama base_url must use "
            "http or https."
        )

    if parsed.hostname not in _LOOPBACK_HOSTS:
        raise ValueError(
            "OllamaProvider only permits "
            "loopback addresses."
        )

    return normalized


def _optional_nonnegative_int(
    *,
    payload: dict[str, object],
    field_name: str,
) -> int | None:
    """Read an optional non-negative integer."""

    value = payload.get(
        field_name
    )

    if value is None:
        return None

    if (
        isinstance(value, bool)
        or not isinstance(
            value,
            int,
        )
        or value < 0
    ):
        raise ProviderInvalidResponseError(
            f"Ollama field {field_name!r} "
            "must be a non-negative integer "
            "when provided."
        )

    return value


def _optional_nonblank_string(
    *,
    payload: dict[str, object],
    field_name: str,
) -> str | None:
    """Read optional non-blank string metadata."""

    value = payload.get(
        field_name
    )

    if value is None:
        return None

    if (
        not isinstance(
            value,
            str,
        )
        or not value.strip()
    ):
        raise ProviderInvalidResponseError(
            f"Ollama field {field_name!r} "
            "must be a non-blank string "
            "when provided."
        )

    return value


class OllamaProvider:
    """Provider adapter for a local Ollama server."""

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_OLLAMA_BASE_URL,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        transport: OllamaTransport | None = None,
    ) -> None:
        if (
            not math.isfinite(
                timeout_seconds
            )
            or timeout_seconds <= 0
        ):
            raise ValueError(
                "timeout_seconds must be "
                "finite and positive."
            )

        self._base_url = (
            _validate_base_url(
                base_url
            )
        )

        self._timeout_seconds = (
            timeout_seconds
        )

        self._transport = (
            transport
            if transport is not None
            else _default_transport
        )

    @property
    def provider_name(self) -> str:
        """Return the provider identifier."""

        return "ollama"

    @property
    def base_url(self) -> str:
        """Return the validated local server URL."""

        return self._base_url

    @property
    def timeout_seconds(self) -> float:
        """Return the request timeout."""

        return self._timeout_seconds

    def generate(
        self,
        *,
        request: EvaluationRequest,
        configuration: ModelConfiguration,
    ) -> ProviderResponse:
        """Generate one response with local Ollama."""

        if (
            configuration.provider
            != self.provider_name
        ):
            raise ValueError(
                "Model configuration provider does not "
                "match Ollama provider adapter."
            )

        payload: dict[str, object] = {
            "model": (
                configuration.requested_model
            ),
            "prompt": request.prompt_text,
            "stream": False,
        }

        if (
            configuration.system_instruction
            is not None
        ):
            payload["system"] = (
                configuration.system_instruction
            )

        options: dict[str, object] = {}

        if (
            configuration.max_output_tokens
            is not None
        ):
            options["num_predict"] = (
                configuration.max_output_tokens
            )

        if (
            configuration.temperature
            is not None
        ):
            options["temperature"] = (
                configuration.temperature
            )

        if configuration.top_p is not None:
            options["top_p"] = (
                configuration.top_p
            )

        if configuration.seed is not None:
            options["seed"] = (
                configuration.seed
            )

        if options:
            payload["options"] = options

        raw_response = self._transport(
            (
                f"{self._base_url}"
                "/api/generate"
            ),
            payload,
            self._timeout_seconds,
        )

        if not isinstance(
            raw_response,
            dict,
        ):
            raise ProviderInvalidResponseError(
                "Ollama response was not "
                "a JSON object."
            )

        provider_error = raw_response.get(
            "error"
        )

        if provider_error is not None:
            if (
                isinstance(
                    provider_error,
                    str,
                )
                and provider_error.strip()
            ):
                raise ProviderError(
                    provider_error.strip()
                )

            raise ProviderError(
                "Ollama returned an "
                "unspecified provider error."
            )

        done = raw_response.get(
            "done"
        )

        if done is not True:
            raise ProviderInvalidResponseError(
                "Ollama non-streaming response "
                "did not report done=true."
            )

        response_text = raw_response.get(
            "response"
        )

        if not isinstance(
            response_text,
            str,
        ):
            raise ProviderInvalidResponseError(
                "Ollama response did not contain "
                "string response text."
            )

        returned_model = (
            _optional_nonblank_string(
                payload=raw_response,
                field_name="model",
            )
        )

        finish_reason = (
            _optional_nonblank_string(
                payload=raw_response,
                field_name="done_reason",
            )
        )

        input_tokens = (
            _optional_nonnegative_int(
                payload=raw_response,
                field_name=(
                    "prompt_eval_count"
                ),
            )
        )

        output_tokens = (
            _optional_nonnegative_int(
                payload=raw_response,
                field_name="eval_count",
            )
        )

        total_tokens: int | None = None

        if (
            input_tokens is not None
            and output_tokens is not None
        ):
            total_tokens = (
                input_tokens
                + output_tokens
            )

        usage: ProviderUsage | None = None

        if (
            input_tokens is not None
            or output_tokens is not None
        ):
            usage = ProviderUsage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
            )

        return ProviderResponse(
            text=response_text,
            provider_request_id=None,
            usage=usage,
            returned_model=returned_model,
            finish_reason=finish_reason,
        )