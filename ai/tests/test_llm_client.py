import json

import httpx
import pytest

from common.enums import Agent
from llm import client
from llm.client import LLMError, call, complete
from llm.config import AgentSpec, ProviderSpec, get_config

CLOUD = ProviderSpec(name="cloud", base_url="https://llm.example/v1", api_key_env="TEST_LLM_KEY")
LOCAL = ProviderSpec(name="local", base_url="http://localhost:11434/v1",
                     base_url_env="TEST_LLM_URL", local=True)


def make_spec(provider: ProviderSpec = CLOUD) -> AgentSpec:
    return AgentSpec(agent=Agent.AFFORDABILITY, provider=provider, model="test-model",
                     timeout_s=5, temperature=0.2)


def ok(text: str = "hello") -> httpx.Response:
    return httpx.Response(200, json={"choices": [{"message": {"content": text}}]})


def fake_provider(*answers):
    queue = list(answers)
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        answer = queue.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer

    return httpx.MockTransport(handler), requests


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("TEST_LLM_KEY", "test-key")
    monkeypatch.delenv("TEST_LLM_URL", raising=False)


def test_success_returns_text_model_and_provider():
    transport, _ = fake_provider(ok("hi there"))
    result = call(make_spec(), "system text", "user text", transport=transport)
    assert result.text == "hi there"
    assert result.model == "test-model"
    assert result.provider == "cloud"
    assert result.latency_s >= 0


def test_request_is_openai_compatible():
    transport, requests = fake_provider(ok())
    call(make_spec(), "system text", "user text", transport=transport)
    request = requests[0]
    assert str(request.url) == "https://llm.example/v1/chat/completions"
    assert request.headers["Authorization"] == "Bearer test-key"
    body = json.loads(request.content)
    assert body["model"] == "test-model"
    assert body["temperature"] == 0.2
    assert body["messages"] == [{"role": "system", "content": "system text"},
                                {"role": "user", "content": "user text"}]
    assert "response_format" not in body


def test_json_mode_asks_for_json():
    transport, requests = fake_provider(ok('{"ok": true}'))
    call(make_spec(), "s", "u", json_mode=True, transport=transport)
    assert json.loads(requests[0].content)["response_format"] == {"type": "json_object"}


def test_missing_key_fails_before_any_request(monkeypatch):
    monkeypatch.delenv("TEST_LLM_KEY")
    transport, requests = fake_provider(ok())
    with pytest.raises(LLMError, match="TEST_LLM_KEY is not set"):
        call(make_spec(), "s", "u", transport=transport)
    assert requests == []


def test_local_model_sends_no_key():
    transport, requests = fake_provider(ok())
    call(make_spec(LOCAL), "s", "u", transport=transport)
    assert "Authorization" not in requests[0].headers


def test_base_url_can_be_overridden_by_env(monkeypatch):
    monkeypatch.setenv("TEST_LLM_URL", "http://host.docker.internal:11434/v1")
    transport, requests = fake_provider(ok())
    call(make_spec(LOCAL), "s", "u", transport=transport)
    assert requests[0].url.host == "host.docker.internal"


def test_error_message_never_contains_the_key():
    transport, _ = fake_provider(httpx.Response(401, json={"error": "invalid key"}))
    with pytest.raises(LLMError) as caught:
        call(make_spec(), "s", "u", transport=transport)
    assert "test-key" not in str(caught.value)
    assert "TEST_LLM_KEY" in str(caught.value)


def test_timeout_is_retried_once_then_fails():
    transport, requests = fake_provider(httpx.ReadTimeout("slow"), httpx.ReadTimeout("slow"))
    with pytest.raises(LLMError, match="no answer within 5 s"):
        call(make_spec(), "s", "u", transport=transport)
    assert len(requests) == 2


def test_timeout_then_success():
    transport, requests = fake_provider(httpx.ReadTimeout("slow"), ok("second try"))
    assert call(make_spec(), "s", "u", transport=transport).text == "second try"
    assert len(requests) == 2


def test_server_error_is_retried():
    transport, requests = fake_provider(httpx.Response(503), ok("recovered"))
    assert call(make_spec(), "s", "u", transport=transport).text == "recovered"
    assert len(requests) == 2


def test_server_error_twice_shows_the_provider_message():
    crash = httpx.Response(500, json={"error": {"message": "llama-server process has terminated"}})
    transport, requests = fake_provider(crash, crash)
    with pytest.raises(LLMError, match="HTTP 500.*llama-server process has terminated"):
        call(make_spec(LOCAL), "s", "u", transport=transport)
    assert len(requests) == 2


def test_wrong_key_is_not_retried():
    transport, requests = fake_provider(httpx.Response(401))
    with pytest.raises(LLMError, match="401"):
        call(make_spec(), "s", "u", transport=transport)
    assert len(requests) == 1


def test_rate_limit_is_reported():
    transport, _ = fake_provider(httpx.Response(429))
    with pytest.raises(LLMError, match="rate limit"):
        call(make_spec(), "s", "u", transport=transport)


def test_ollama_not_running():
    transport, _ = fake_provider(httpx.ConnectError("refused"))
    with pytest.raises(LLMError, match="is Ollama running"):
        call(make_spec(LOCAL), "s", "u", transport=transport)


def test_unexpected_response_format():
    transport, _ = fake_provider(httpx.Response(200, json={"something": "else"}))
    with pytest.raises(LLMError, match="unexpected response format"):
        call(make_spec(), "s", "u", transport=transport)


def test_empty_answer():
    transport, _ = fake_provider(ok("   "))
    with pytest.raises(LLMError, match="empty answer"):
        call(make_spec(), "s", "u", transport=transport)


def test_complete_uses_the_agent_from_models_toml(monkeypatch):
    seen = {}

    def fake_call(spec, system, user, json_mode=False):
        seen["spec"] = spec
        return "result"

    monkeypatch.setattr(client, "call", fake_call)
    assert complete(Agent.VALUATION, "s", "u") == "result"
    assert seen["spec"] == get_config()[Agent.VALUATION]
