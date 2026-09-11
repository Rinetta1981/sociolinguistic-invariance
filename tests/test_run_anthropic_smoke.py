import argparse
import sys
from pathlib import Path

import pytest

import scripts.run_anthropic_smoke as smoke_module
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
from sociolinguistic_invariance.provenance import (
    GitProvenance,
)
from sociolinguistic_invariance.provider import (
    ProviderResponse,
    ScriptedMockProvider,
)

PROMPT_TEXT = (
    "Η Μαδρίτη είναι η πρωτεύουσα "
    "της Πορτογαλίας. Γιατί;"
)

VALID_COMMIT = "a" * 40
VALID_STATUS_SHA256 = "b" * 64


def _parser() -> argparse.ArgumentParser:
    """Create the smoke-test argument parser."""

    return smoke_module._build_parser()


def _clean_provenance() -> GitProvenance:
    """Create clean Git provenance."""

    return GitProvenance(
        available=True,
        commit=VALID_COMMIT,
        worktree_clean=True,
        status_entry_count=0,
        status_sha256=VALID_STATUS_SHA256,
    )


def _dirty_provenance() -> GitProvenance:
    """Create dirty Git provenance."""

    return GitProvenance(
        available=True,
        commit=VALID_COMMIT,
        worktree_clean=False,
        status_entry_count=1,
        status_sha256=VALID_STATUS_SHA256,
    )


def _unavailable_provenance() -> GitProvenance:
    """Create unavailable Git provenance."""

    return GitProvenance(
        available=False,
        commit=None,
        worktree_clean=None,
        status_entry_count=0,
        status_sha256=None,
    )


def _request() -> EvaluationRequest:
    """Create one evaluation request."""

    return EvaluationRequest(
        run_id="run_smoke_test",
        request_id="req_smoke_test",
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


def _configuration() -> ModelConfiguration:
    """Create an Anthropic-compatible configuration."""

    return ModelConfiguration(
        provider="anthropic",
        requested_model="claude-test-model",
        temperature=None,
        top_p=None,
        max_output_tokens=128,
        seed=None,
        system_instruction=(
            "Answer the user's request directly "
            "and accurately."
        ),
        sdk_version="1.5.0",
    )


class ProviderMustNotBeConstructed:
    """Fail if a safety gate allows provider creation."""

    @classmethod
    def from_environment(
        cls,
    ) -> None:
        raise AssertionError(
            "Provider must not be constructed."
        )


def test_help_describes_live_execution_risk() -> None:
    parser = _parser()

    help_text = parser.format_help()

    assert "--model" in help_text
    assert "--execute-live" in help_text

    assert (
        "real external API call"
        in help_text
    )

    assert (
        "may incur cost"
        in help_text
    )


def test_live_confirmation_is_required() -> None:
    parser = _parser()

    with pytest.raises(
        SystemExit,
    ) as error:
        smoke_module._require_live_confirmation(
            confirmed=False,
            parser=parser,
        )

    assert error.value.code == 2


def test_live_confirmation_accepts_explicit_authorization() -> None:
    smoke_module._require_live_confirmation(
        confirmed=True,
        parser=_parser(),
    )


def test_live_execution_rejects_unavailable_git_provenance() -> None:
    parser = _parser()

    with pytest.raises(
        SystemExit,
    ) as error:
        smoke_module._require_clean_provenance(
            provenance=_unavailable_provenance(),
            parser=parser,
        )

    assert error.value.code == 2


def test_live_execution_rejects_dirty_git_worktree() -> None:
    parser = _parser()

    with pytest.raises(
        SystemExit,
    ) as error:
        smoke_module._require_clean_provenance(
            provenance=_dirty_provenance(),
            parser=parser,
        )

    assert error.value.code == 2


def test_live_execution_accepts_clean_git_provenance() -> None:
    smoke_module._require_clean_provenance(
        provenance=_clean_provenance(),
        parser=_parser(),
    )


def test_api_key_is_required(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(
        "ANTHROPIC_API_KEY",
        raising=False,
    )

    with pytest.raises(
        SystemExit,
    ) as error:
        smoke_module._require_api_key(
            parser=_parser(),
        )

    assert error.value.code == 2


def test_blank_api_key_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "ANTHROPIC_API_KEY",
        "   ",
    )

    with pytest.raises(
        SystemExit,
    ) as error:
        smoke_module._require_api_key(
            parser=_parser(),
        )

    assert error.value.code == 2


def test_nonblank_api_key_passes_gate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "ANTHROPIC_API_KEY",
        "fake-test-key",
    )

    smoke_module._require_api_key(
        parser=_parser(),
    )


def test_request_serialization() -> None:
    request = _request()

    serialized = (
        smoke_module._request_to_dict(
            request
        )
    )

    assert serialized == {
        "run_id": "run_smoke_test",
        "request_id": "req_smoke_test",
        "family_id": "FP_0001",
        "task_type": (
            "false_premise_correction"
        ),
        "condition": "standard",
        "prompt_text": PROMPT_TEXT,
        "prompt_sha256": (
            sha256_text(
                PROMPT_TEXT
            )
        ),
        "order_index": 0,
    }


def test_configuration_serialization() -> None:
    serialized = (
        smoke_module._configuration_to_dict(
            _configuration()
        )
    )

    assert serialized == {
        "provider": "anthropic",
        "requested_model": (
            "claude-test-model"
        ),
        "temperature": None,
        "top_p": None,
        "max_output_tokens": 128,
        "seed": None,
        "system_instruction": (
            "Answer the user's request directly "
            "and accurately."
        ),
        "sdk_version": "1.5.0",
    }


def test_smoke_output_path_uses_run_id() -> None:
    path = smoke_module._smoke_output_path(
        run_id="run_example"
    )

    assert path == (
        smoke_module.REPO_ROOT
        / "results"
        / "smoke"
        / "run_example.json"
    )


def test_main_without_live_flag_stops_before_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        smoke_module,
        "AnthropicProvider",
        ProviderMustNotBeConstructed,
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_anthropic_smoke.py",
            "--model",
            "claude-test-model",
        ],
    )

    with pytest.raises(
        SystemExit,
    ) as error:
        smoke_module.main()

    assert error.value.code == 2


def test_main_dirty_worktree_stops_before_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "ANTHROPIC_API_KEY",
        "fake-test-key",
    )

    monkeypatch.setattr(
        smoke_module,
        "AnthropicProvider",
        ProviderMustNotBeConstructed,
    )

    monkeypatch.setattr(
        smoke_module,
        "capture_git_provenance",
        lambda _: _dirty_provenance(),
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_anthropic_smoke.py",
            "--model",
            "claude-test-model",
            "--execute-live",
        ],
    )

    with pytest.raises(
        SystemExit,
    ) as error:
        smoke_module.main()

    assert error.value.code == 2


def test_main_missing_api_key_stops_before_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(
        "ANTHROPIC_API_KEY",
        raising=False,
    )

    monkeypatch.setattr(
        smoke_module,
        "AnthropicProvider",
        ProviderMustNotBeConstructed,
    )

    monkeypatch.setattr(
        smoke_module,
        "capture_git_provenance",
        lambda _: _clean_provenance(),
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_anthropic_smoke.py",
            "--model",
            "claude-test-model",
            "--execute-live",
        ],
    )

    with pytest.raises(
        SystemExit,
    ) as error:
        smoke_module.main()

    assert error.value.code == 2


def test_main_executes_exactly_one_fake_provider_request(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    usage = ProviderUsage(
        input_tokens=20,
        output_tokens=10,
        total_tokens=30,
    )

    provider = ScriptedMockProvider(
        provider_name="anthropic",
        actions=[
            ProviderResponse(
                text=(
                    "Η Μαδρίτη είναι η "
                    "πρωτεύουσα της Ισπανίας."
                ),
                provider_request_id=(
                    "provider-request-1"
                ),
                usage=usage,
                returned_model=(
                    "claude-returned-model"
                ),
                finish_reason="end_turn",
            )
        ],
    )

    class FakeAnthropicProviderFactory:
        """Return the local fake provider."""

        @classmethod
        def from_environment(
            cls,
        ) -> ScriptedMockProvider:
            return provider

    captured: dict[str, object] = {}

    def fake_write_raw_results_atomic(
        *,
        path: Path,
        payload: dict[str, object],
        overwrite: bool = False,
    ) -> None:
        captured["path"] = path
        captured["payload"] = payload
        captured["overwrite"] = overwrite

    monkeypatch.setenv(
        "ANTHROPIC_API_KEY",
        "fake-test-key",
    )

    monkeypatch.setattr(
        smoke_module,
        "AnthropicProvider",
        FakeAnthropicProviderFactory,
    )

    monkeypatch.setattr(
        smoke_module,
        "capture_git_provenance",
        lambda _: _clean_provenance(),
    )

    monkeypatch.setattr(
        smoke_module,
        "new_run_id",
        lambda: "run_fake_live_test",
    )

    monkeypatch.setattr(
        smoke_module,
        "write_raw_results_atomic",
        fake_write_raw_results_atomic,
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_anthropic_smoke.py",
            "--model",
            "claude-test-model",
            "--execute-live",
        ],
    )

    exit_code = smoke_module.main()

    assert exit_code == 0

    assert len(
        provider.calls
    ) == 1

    assert (
        provider.remaining_action_count
        == 0
    )

    call = provider.calls[
        0
    ]

    assert call.requested_model == (
        "claude-test-model"
    )

    assert call.request_id

    payload = captured[
        "payload"
    ]

    assert isinstance(
        payload,
        dict,
    )

    assert payload["artifact_type"] == (
        "anthropic_live_smoke"
    )

    assert payload[
        "live_smoke_format_version"
    ] == "anthropic-live-smoke-v0.1"

    assert payload[
        "planned_request_count"
    ] == 12

    assert payload[
        "executed_request_count"
    ] == 1

    assert payload[
        "provider_attempt_limit"
    ] == 1

    assert payload[
        "benchmark_claim_eligible"
    ] is False

    request_payload = payload[
        "request"
    ]

    assert isinstance(
        request_payload,
        dict,
    )

    assert request_payload[
        "family_id"
    ] == "FP_0001"

    assert request_payload[
        "condition"
    ] == "standard"

    result_payload = payload[
        "result"
    ]

    assert isinstance(
        result_payload,
        dict,
    )

    assert result_payload[
        "status"
    ] == "SUCCESS"

    assert result_payload[
        "returned_model"
    ] == "claude-returned-model"

    assert result_payload[
        "finish_reason"
    ] == "end_turn"

    assert result_payload[
        "provider_request_id"
    ] == "provider-request-1"

    output_path = captured[
        "path"
    ]

    assert isinstance(
        output_path,
        Path,
    )

    assert output_path.name == (
        "run_fake_live_test.json"
    )

    assert captured[
        "overwrite"
    ] is False

    stdout = capsys.readouterr().out

    assert (
        "Maximum external provider attempts: 1"
        in stdout
    )

    assert (
        "Benchmark claim eligible: False"
        in stdout
    )