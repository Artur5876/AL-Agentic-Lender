from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.repository import InMemoryRepository

SETTINGS = Settings(repository="memory", auth_mode="dev", default_broker_uid="broker-ciaran")
BORROWER = {"Authorization": "Bearer dev:borrower-aoife:borrower"}
APPLICATION = {
    "buyerType": "first_time",
    "financials": {"grossAnnualIncome": 95000, "monthlyDebts": 300, "deposit": 60000,
                   "loanAmount": 335000, "termYears": 30},
    "property": {"county": "Cork", "floorAreaM2": 110, "bedrooms": 3,
                 "propertyType": "semi_detached", "ber": "B2", "askingPrice": 395000},
}
ORDER = ["01-affordability", "02-valuation", "03-market_research", "04-underwriting_strategist"]
MODEL_AGENTS = ("affordability", "valuation", "underwriting_strategist")


@pytest.fixture
def stored(ai_committee):
    repo = InMemoryRepository()
    client = TestClient(create_app(SETTINGS, repo, committee=ai_committee))
    r = client.post("/applications", json=APPLICATION, headers=BORROWER)
    assert r.status_code == 201
    return repo.get_deliberation(r.json()["id"])


def test_every_agent_step_is_stored_in_order(stored):
    assert [s["id"] for s in stored["steps"]] == ORDER
    assert stored["isStub"] is False


def test_each_step_has_output_reasoning_model_and_timestamp(stored):
    for s in stored["steps"]:
        assert isinstance(s["output"], dict), s["id"]
        assert isinstance(s["reasoning"], str) and s["reasoning"], s["id"]
        assert isinstance(s["model"], str) and s["model"], s["id"]
        assert datetime.fromisoformat(s["timestamp"]).utcoffset() == timedelta(0), s["id"]


def test_the_model_each_agent_used_is_recorded(stored):
    models = {s["agent"]: s["model"] for s in stored["steps"]}
    assert models == {"affordability": "fake-affordability", "valuation": "fake-valuation",
                      "market_research": "none",
                      "underwriting_strategist": "fake-underwriting_strategist"}


def test_audit_details_are_kept(stored):
    steps = {s["agent"]: s for s in stored["steps"]}
    for agent in MODEL_AGENTS:
        assert steps[agent]["provider"] == "fake"
        assert steps[agent]["promptVersion"], agent
        assert steps[agent]["input"], agent
        assert steps[agent]["verdict"], agent
    assert steps["affordability"]["input"]["lti"] == 3.5263 
    assert steps["market_research"]["stub"] is True


def test_the_final_decision_matches_the_strategist_step(stored):
    final = stored["steps"][-1]
    assert stored["finalDecision"] == final["verdict"] == final["output"]["decision"]
    assert stored["creditMemo"] == final["output"]["creditMemo"]