from pathlib import Path

import pytest

from common.enums import Agent
from llm.config import ConfigError, load_config

VALID = """
[defaults]
timeout_s = 30
temperature = 0.2

[providers.cloud_a]
base_url = "https://a.example/v1"
api_key_env = "A_KEY"

[providers.cloud_b]
base_url = "https://b.example/v1"
api_key_env = "B_KEY"
timeout_s = 45

[providers.local]
base_url = "http://localhost:11434/v1"
local = true

[agents.affordability]
provider = "cloud_a"
model = "model-a"

[agents.valuation]
provider = "local"
model = "model-local"

[agents.market_research]
provider = "cloud_b"
model = "model-b"

[agents.underwriting_strategist]
provider = "cloud_b"
model = "model-b"
timeout_s = 60
"""


def write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "models.toml"
    path.write_text(text, encoding="utf-8")
    return path


def test_default_config_loads():
    config = load_config()
    assert set(config) == set(Agent)


def test_default_config_meets_us421():
    used = {spec.provider for spec in load_config().values()}
    cloud = {p.name for p in used if not p.local}
    local = {p.name for p in used if p.local}
    assert len(cloud) >= 2
    assert len(local) >= 1


def test_load_needs_no_secrets(monkeypatch):
    monkeypatch.delenv("AL_GROQ_API_KEY", raising=False)
    monkeypatch.delenv("AL_GEMINI_API_KEY", raising=False)
    assert load_config()


def test_valid_config(tmp_path):
    spec = load_config(write(tmp_path, VALID))[Agent.VALUATION]
    assert spec.provider.name == "local"
    assert spec.provider.local is True
    assert spec.model == "model-local"
    assert spec.temperature == 0.2


def test_timeout_precedence(tmp_path):
    config = load_config(write(tmp_path, VALID))
    assert config[Agent.AFFORDABILITY].timeout_s == 30
    assert config[Agent.MARKET_RESEARCH].timeout_s == 45
    assert config[Agent.UNDERWRITING_STRATEGIST].timeout_s == 60


def test_unknown_provider_rejected(tmp_path):
    text = VALID.replace('provider = "local"', 'provider = "olama"')
    with pytest.raises(ConfigError, match="valuation.*olama"):
        load_config(write(tmp_path, text))


def test_missing_agent_rejected(tmp_path):
    text = VALID.split("[agents.underwriting_strategist]")[0]
    with pytest.raises(ConfigError, match="underwriting_strategist"):
        load_config(write(tmp_path, text))


def test_cloud_provider_without_key_env_rejected(tmp_path):
    text = VALID.replace('api_key_env = "A_KEY"\n', "")
    with pytest.raises(ConfigError, match="cloud_a"):
        load_config(write(tmp_path, text))


def test_non_positive_timeout_rejected(tmp_path):
    text = VALID.replace("timeout_s = 30", "timeout_s = 0")
    with pytest.raises(ConfigError, match="timeout_s"):
        load_config(write(tmp_path, text))


def test_typo_key_rejected(tmp_path):
    text = VALID.replace("timeout_s = 60", "timout_s = 60")
    with pytest.raises(ConfigError, match="timout_s"):
        load_config(write(tmp_path, text))


def test_broken_toml_rejected(tmp_path):
    with pytest.raises(ConfigError, match="not valid TOML"):
        load_config(write(tmp_path, "[agents\nprovider = "))
