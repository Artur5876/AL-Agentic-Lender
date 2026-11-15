from __future__ import annotations

import tomllib
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from common.enums import Agent

CONFIG_PATH = Path(__file__).with_name("models.toml")
FALLBACK_TIMEOUT_S = 30.0
FALLBACK_TEMPERATURE = 0.2

TOP_KEYS = {"defaults", "providers", "agents"}
DEFAULT_KEYS = {"timeout_s", "temperature"}
PROVIDER_KEYS = {"base_url", "base_url_env", "api_key_env", "local", "timeout_s"}
AGENT_KEYS = {"provider", "model", "timeout_s", "temperature"}


class ConfigError(ValueError):
    """models.toml is missing something or has a wrong value."""


@dataclass(frozen=True)
class ProviderSpec:
    name: str
    base_url: str
    base_url_env: str | None = None
    api_key_env: str | None = None
    local: bool = False
    timeout_s: float | None = None


@dataclass(frozen=True)
class AgentSpec:
    agent: Agent
    provider: ProviderSpec
    model: str
    timeout_s: float
    temperature: float

def _check_keys(where: str, data: dict, allowed: set[str]) -> None:
    unknown = set(data) - allowed
    if unknown:
        raise ConfigError(f"{where}: unknown key(s) {', '.join(sorted(unknown))}")


def _number(where: str, name: str, value: object, *, allow_zero: bool = False) -> float:
    is_number = isinstance(value, int | float) and not isinstance(value, bool)
    if not is_number or value < 0 or (value == 0 and not allow_zero):
        rule = ">= 0" if allow_zero else "> 0"
        raise ConfigError(f"{where}: {name} must be a number {rule}, got {value!r}")
    return float(value)

def _parse_provider(name: str, data: dict) -> ProviderSpec:
    where = f"provider '{name}'"
    _check_keys(where, data, PROVIDER_KEYS)

    base_url = data.get("base_url")
    if not isinstance(base_url, str) or not base_url.startswith(("http://", "https://")):
        raise ConfigError(f"{where}: base_url must start with http:// or https://")

    local = data.get("local", False)
    api_key_env = data.get("api_key_env")
    if not local and not api_key_env:
        raise ConfigError(f"{where}: a cloud provider needs api_key_env")

    timeout = data.get("timeout_s")
    return ProviderSpec(
        name=name,
        base_url=base_url,
        base_url_env=data.get("base_url_env"),
        api_key_env=api_key_env,
        local=local,
        timeout_s=None if timeout is None else _number(where, "timeout_s", timeout),
    )

def _parse_agent(name: str, data: dict, providers: dict[str, ProviderSpec],
                 default_timeout: float, default_temperature: float) -> AgentSpec:
    where = f"agent '{name}'"
    _check_keys(where, data, AGENT_KEYS)

    provider_name = data.get("provider")
    if provider_name not in providers:
        known = ", ".join(sorted(providers))
        raise ConfigError(f"{where}: unknown provider {provider_name!r} (known: {known})")
    provider = providers[provider_name]

    model = data.get("model")
    if not isinstance(model, str) or not model.strip():
        raise ConfigError(f"{where}: model must be a non-empty string")

    timeout = data.get("timeout_s")
    if timeout is None:
        timeout = provider.timeout_s if provider.timeout_s is not None else default_timeout
    temperature = data.get("temperature", default_temperature)

    return AgentSpec(
        agent=Agent(name),
        provider=provider,
        model=model,
        timeout_s=_number(where, "timeout_s", timeout),
        temperature=_number(where, "temperature", temperature, allow_zero=True),
    )

def load_config(path: Path = CONFIG_PATH) -> dict[Agent, AgentSpec]:
    try:
        with open(path, "rb") as f:  # tomllib needs binary mode
            raw = tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"{path.name} is not valid TOML: {e}") from e
    _check_keys(path.name, raw, TOP_KEYS)

    defaults = raw.get("defaults", {})
    _check_keys("[defaults]", defaults, DEFAULT_KEYS)
    default_timeout = _number("[defaults]", "timeout_s",
                              defaults.get("timeout_s", FALLBACK_TIMEOUT_S))
    default_temperature = _number("[defaults]", "temperature",
                                  defaults.get("temperature", FALLBACK_TEMPERATURE),
                                  allow_zero=True)

    providers = {name: _parse_provider(name, data)
                 for name, data in raw.get("providers", {}).items()}

    agents = raw.get("agents", {})
    expected = {a.value for a in Agent}
    missing, extra = expected - set(agents), set(agents) - expected
    if missing or extra:
        raise ConfigError(f"agents must be exactly {', '.join(sorted(expected))}; "
                          f"missing: {sorted(missing)}, unknown: {sorted(extra)}")

    return {Agent(name): _parse_agent(name, data, providers, default_timeout,
                                      default_temperature)
            for name, data in agents.items()}


@lru_cache(maxsize=1)
def get_config() -> dict[Agent, AgentSpec]:
    return load_config()