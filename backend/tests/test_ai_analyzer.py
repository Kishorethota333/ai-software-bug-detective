import asyncio
import json
from types import SimpleNamespace

import pytest
from google.genai import errors

from app.ai import analyzer
from app.config.settings import settings


def analysis_payload():
    return {
        "root_cause": "The input validation path accepts an unexpected value.",
        "confidence": 0.82,
        "severity": "MEDIUM",
        "affected_component": "API validation",
        "possible_causes": "Missing validation or an unexpected request shape.",
        "suggested_fix": "Validate the input before processing it.",
        "recommended_actions": "Add a regression test for the invalid value.",
        "test_cases": [
            {
                "scenario": "Reject unexpected input",
                "input_data": "Malformed request",
                "expected_result": "A controlled validation response",
                "priority": "HIGH",
                "test_type": "NEGATIVE",
            }
        ],
    }


def install_fake_gemini_client(monkeypatch, *, text=None, error=None, delay=0):
    captured = {}

    class FakeModels:
        async def generate_content(self, **kwargs):
            captured["request"] = kwargs
            if delay:
                await asyncio.sleep(delay)
            if error:
                raise error
            return SimpleNamespace(text=text)

    class FakeAsyncClient:
        def __init__(self):
            self.models = FakeModels()

        async def aclose(self):
            captured["closed"] = True

    class FakeClient:
        def __init__(self, **kwargs):
            captured["client_options"] = kwargs
            self.aio = FakeAsyncClient()

    monkeypatch.setattr(analyzer.genai, "Client", FakeClient)
    return captured


def test_mock_provider_remains_available_when_explicitly_selected(monkeypatch):
    monkeypatch.setattr(settings, "ai_provider", "mock")
    monkeypatch.setattr(settings, "ai_api_key", "")
    monkeypatch.setattr(settings, "gemini_api_key", "")

    result = asyncio.run(analyzer.analyze("API error 500"))

    assert result["provider"] == "mock (set AI_PROVIDER and AI_API_KEY for live AI)"
    assert result["root_cause"]
    assert result["test_cases"]


def test_gemini_provider_uses_configured_model_and_contract(monkeypatch):
    monkeypatch.setattr(settings, "ai_provider", "gemini")
    monkeypatch.setattr(settings, "gemini_api_key", "test-key-not-a-real-credential")
    monkeypatch.setattr(settings, "gemini_model", "gemini-test-model")
    captured = install_fake_gemini_client(
        monkeypatch, text=json.dumps(analysis_payload())
    )

    result = asyncio.run(analyzer.analyze("approved source and sanitized error"))

    request = captured["request"]
    assert captured["client_options"]["api_key"] == "test-key-not-a-real-credential"
    assert captured["client_options"]["http_options"].timeout == 45_000
    assert request["model"] == "gemini-test-model"
    assert request["contents"] == "approved source and sanitized error"
    assert request["config"].response_mime_type == "application/json"
    assert result["provider"] == "gemini"
    assert result["test_cases"][0]["scenario"] == "Reject unexpected input"
    assert captured["closed"] is True


def test_gemini_zero_division_analysis_requests_positive_and_safe_error_cases(monkeypatch):
    monkeypatch.setattr(settings, "ai_provider", "gemini")
    monkeypatch.setattr(settings, "gemini_api_key", "test-key-not-a-real-credential")
    cases = [
        {
            "scenario": "Positive division",
            "input_data": "10 / 2",
            "expected_result": "5",
            "priority": "HIGH",
            "test_type": "POSITIVE",
        },
        {
            "scenario": "Division by zero",
            "input_data": "10 / 0",
            "expected_result": "Return a controlled error without an unhandled exception",
            "priority": "HIGH",
            "test_type": "NEGATIVE",
        },
    ]
    captured = install_fake_gemini_client(
        monkeypatch, text=json.dumps({**analysis_payload(), "test_cases": cases})
    )

    result = asyncio.run(
        analyzer.analyze("ZeroDivisionError when calculating 10 / denominator")
    )

    instruction = captured["request"]["config"].system_instruction
    assert "10 / 2 returns 5" in instruction
    assert "10 / 0" in instruction
    assert [case["input_data"] for case in result["test_cases"]] == ["10 / 2", "10 / 0"]
    assert result["test_cases"][0]["expected_result"] == "5"
    assert "controlled error" in result["test_cases"][1]["expected_result"]


def test_gemini_requires_its_own_api_key(monkeypatch):
    monkeypatch.setattr(settings, "ai_provider", "gemini")
    monkeypatch.setattr(settings, "gemini_api_key", "")
    monkeypatch.setattr(settings, "ai_api_key", "unrelated-provider-key")

    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        asyncio.run(analyzer.analyze("diagnostic context"))


def test_gemini_rate_limit_is_reported_without_fallback(monkeypatch):
    monkeypatch.setattr(settings, "ai_provider", "gemini")
    monkeypatch.setattr(settings, "gemini_api_key", "test-key-not-a-real-credential")
    install_fake_gemini_client(
        monkeypatch,
        error=errors.APIError(429, {"error": {"message": "rate limited"}}),
    )

    with pytest.raises(ValueError, match="rate limit or quota"):
        asyncio.run(analyzer.analyze("diagnostic context"))


def test_gemini_api_failure_is_reported_without_provider_details(monkeypatch):
    monkeypatch.setattr(settings, "ai_provider", "gemini")
    monkeypatch.setattr(settings, "gemini_api_key", "test-key-not-a-real-credential")
    install_fake_gemini_client(
        monkeypatch,
        error=errors.APIError(503, {"error": {"message": "provider diagnostic"}}),
    )

    with pytest.raises(ValueError, match="HTTP 503") as error:
        asyncio.run(analyzer.analyze("diagnostic context"))

    assert "provider diagnostic" not in str(error.value)


def test_gemini_timeout_is_reported(monkeypatch):
    monkeypatch.setattr(settings, "ai_provider", "gemini")
    monkeypatch.setattr(settings, "gemini_api_key", "test-key-not-a-real-credential")
    monkeypatch.setattr(analyzer, "GEMINI_TIMEOUT_SECONDS", 0.01)
    install_fake_gemini_client(
        monkeypatch,
        text=json.dumps(analysis_payload()),
        delay=0.05,
    )

    with pytest.raises(ValueError, match="timed out"):
        asyncio.run(analyzer.analyze("diagnostic context"))


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("not json", "invalid JSON"),
        ("{}", "missing required fields"),
        ("", "empty analysis response"),
        (json.dumps({**analysis_payload(), "confidence": "unknown"}), "confidence"),
    ],
)
def test_gemini_rejects_invalid_responses(monkeypatch, text, message):
    monkeypatch.setattr(settings, "ai_provider", "gemini")
    monkeypatch.setattr(settings, "gemini_api_key", "test-key-not-a-real-credential")
    install_fake_gemini_client(monkeypatch, text=text)

    with pytest.raises(ValueError, match=message):
        asyncio.run(analyzer.analyze("diagnostic context"))


def test_openai_provider_still_uses_existing_chat_completion_contract(monkeypatch):
    monkeypatch.setattr(settings, "ai_provider", "openai")
    monkeypatch.setattr(settings, "ai_api_key", "test-key-not-a-real-credential")

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": json.dumps(analysis_payload())}}]}

    class FakeAsyncClient:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, url, **kwargs):
            captured["url"] = url
            captured["request"] = kwargs["json"]
            return FakeResponse()

    captured = {}
    monkeypatch.setattr(analyzer.httpx, "AsyncClient", FakeAsyncClient)

    result = asyncio.run(analyzer.analyze("diagnostic context"))

    assert captured["url"] == "https://api.openai.com/v1/chat/completions"
    assert captured["request"]["model"] == settings.ai_model
    assert result["provider"] == "openai"
    assert result["test_cases"]
