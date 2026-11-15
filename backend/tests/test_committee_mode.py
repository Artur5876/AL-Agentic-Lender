"""US-414: AL_COMMITTEE_MODE picks the real AI committee or the stub."""

import committee as ai_committee
import pytest

from app import integrations
from app.config import Settings

AI_RESULT = {"decision": "approve", "creditMemo": "memo", "isStub": False, "steps": []}


def use_mode(monkeypatch, mode):
    monkeypatch.setattr(integrations, "get_settings", lambda: Settings(committee_mode=mode))


def test_agents_mode_runs_the_ai_committee(monkeypatch):
    use_mode(monkeypatch, "agents")
    monkeypatch.setattr(ai_committee, "run_committee", lambda application: AI_RESULT)
    assert integrations.run_committee({}) is AI_RESULT


def test_stub_mode_never_calls_the_ai_committee(monkeypatch):
    use_mode(monkeypatch, "stub")
    monkeypatch.setattr(ai_committee, "run_committee",
                        lambda application: pytest.fail("AI committee was called"))
    assert integrations.run_committee({})["isStub"] is True


def test_stub_is_the_default(monkeypatch):
    monkeypatch.delenv("AL_COMMITTEE_MODE", raising=False)
    assert Settings(_env_file=None).committee_mode == "stub"
