from __future__ import annotations

import os
import time
from dataclasses import dataclass

import httpx

from common.enums import Agent
from llm.config import AgentSpec, get_config

RETRIES = 1
RETRY_STATUSES = {500, 502, 503, 504}


class LLMError(RuntimeError):
    def __init__(self, agent: str, provider: str, reason: str):
        super().__init__(f"agent '{agent}' via {provider}: {reason}")
        self.agent = agent
        self.provider = provider
        self.reason = reason


@dataclass(frozen=True)
class LLMResult:
    text: str
    model: str
    provider: str
    latency_s: float


def resolve_base_url(spec: AgentSpec) -> str:
    provider = spec.provider
    if provider.base_url_env and os.environ.get(provider.base_url_env):
        return os.environ[provider.base_url_env]
    return provider.base_url


def _auth_headers(spec: AgentSpec) -> dict[str, str]:
    env_name = spec.provider.api_key_env
    if env_name is None:
        return {}
    key = os.environ.get(env_name)
    if not key:
        raise LLMError(spec.agent, spec.provider.name, f"{env_name} is not set")
    return {"Authorization": f"Bearer {key}"}


def _payload(spec: AgentSpec, system: str, user: str, json_mode: bool) -> dict:
    payload = {
        "model": spec.model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": spec.temperature,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    return payload


def _read_answer(spec: AgentSpec, response: httpx.Response) -> str:
    try:
        text = response.json()["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError):
        raise LLMError(spec.agent, spec.provider.name, "unexpected response format") from None
    if not isinstance(text, str) or not text.strip():
        raise LLMError(spec.agent, spec.provider.name, "empty answer")
    return text


def call(spec: AgentSpec, system: str, user: str, *, json_mode: bool = False,
         transport: httpx.BaseTransport | None = None) -> LLMResult:
    """Send one chat request for `spec`. Raises LLMError if no answer can be had.

    `transport` is only for tests (httpx.MockTransport); production code leaves it None.
    """
    agent, provider = spec.agent, spec.provider.name
    url = resolve_base_url(spec).rstrip("/") + "/chat/completions"
    headers = _auth_headers(spec)  # fails here, before any network call, if the key is missing
    payload = _payload(spec, system, user, json_mode)

    started = time.monotonic()
    last_problem = ""
    with httpx.Client(timeout=spec.timeout_s, transport=transport) as client:
        for _attempt in range(RETRIES + 1):
            try:
                response = client.post(url, json=payload, headers=headers)
            except httpx.TimeoutException:
                last_problem = f"no answer within {spec.timeout_s:g} s"
                continue
            except httpx.ConnectError as e:
                hint = " (is Ollama running?)" if spec.provider.local else ""
                raise LLMError(agent, provider, f"cannot connect to {url}{hint}") from e

            if response.status_code in RETRY_STATUSES:
                last_problem = f"HTTP {response.status_code}: {response.text[:200]}"
                continue
            if response.status_code == 429:
                raise LLMError(agent, provider, "rate limit reached (HTTP 429)")
            if response.status_code in (401, 403):
                raise LLMError(agent, provider,
                               f"HTTP {response.status_code}: check {spec.provider.api_key_env}")
            if response.is_error:
                raise LLMError(agent, provider,
                               f"HTTP {response.status_code}: {response.text[:200]}")

            return LLMResult(
                text=_read_answer(spec, response),
                model=spec.model,
                provider=provider,
                latency_s=round(time.monotonic() - started, 2),
            )

    raise LLMError(agent, provider, f"{last_problem} (after {RETRIES + 1} attempts)")


def complete(agent: Agent | str, system: str, user: str, *, json_mode: bool = False) -> LLMResult:
    return call(get_config()[agent], system, user, json_mode=json_mode)