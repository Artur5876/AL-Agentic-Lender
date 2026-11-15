from datetime import datetime, timedelta

import pytest

from agents.base import AgentError
from committee import run_committee
from common.tests import backend_dict
from llm.client import LLMError
from tests.fakes import agent_llm

AGENTS = ("affordability", "valuation", "market_research", "underwriting_strategist")
STEP_FIELDS = {"agent": str, "model": str, "output": dict, "reasoning": str, "timestamp": str}

GOOD = {
    "affordability": {"verdict": "affordable", "summary": "Comfortable.", "strengths": [],
                      "concerns": []},
    "valuation": {"verdict": "acceptable", "summary": "Price in line.", "concerns": []},
    "underwriting_strategist": {"decision": "approve", "memo": "Approve.", "conditions": []},
}


def application():
    return backend_dict(valuation={"estimate": 380000, "low": 360000, "high": 400000,
                                   "modelVersion": "gbr-1"})


def test_result_matches_the_backend_contract():
    llm, _ = agent_llm(GOOD)
    result = run_committee(application(), llm=llm)

    assert result["decision"] in {"approve", "conditionally_approve", "decline"}
    assert isinstance(result["creditMemo"], str) and result["creditMemo"]
    assert result["isStub"] is False
    assert sorted(s["agent"] for s in result["steps"]) == sorted(AGENTS)
    for s in result["steps"]:
        for field, typ in STEP_FIELDS.items():
            assert isinstance(s[field], typ), (s["agent"], field)
        assert datetime.fromisoformat(s["timestamp"]).utcoffset() == timedelta(0)


def test_agents_run_in_order_and_the_placeholder_calls_no_model():
    llm, calls = agent_llm(GOOD)
    run_committee(application(), llm=llm)
    assert calls == ["affordability", "valuation", "underwriting_strategist"]


def test_decision_and_memo_come_from_the_strategist():
    llm, _ = agent_llm(GOOD)
    result = run_committee(application(), llm=llm)
    final = result["steps"][-1]
    assert final["agent"] == "underwriting_strategist"
    assert result["decision"] == final["output"]["decision"] == "approve"
    assert result["creditMemo"] == final["output"]["creditMemo"]


def test_over_valued_property_ends_in_conditional_approval():
    llm, _ = agent_llm(GOOD)  # every model says "all good"...
    app = backend_dict(valuation={"estimate": 350000, "low": 330000, "high": 370000,
                                  "modelVersion": "gbr-1"})
    app["financials"] |= {"loanAmount": 300000, "deposit": 95000}
    result = run_committee(app, llm=llm)
    assert result["decision"] == "conditionally_approve"
    assert "Valuation" in result["creditMemo"]


def test_low_income_ends_in_decline():
    llm, _ = agent_llm(GOOD)
    app = application()
    app["financials"]["grossAnnualIncome"] = 40_000
    assert run_committee(app, llm=llm)["decision"] == "decline"


@pytest.mark.parametrize("error", [
    LLMError("valuation", "ollama", "cannot connect"),
    AgentError("valuation: no valid answer after 2 tries"),
])
def test_an_agent_failure_reaches_the_backend(error):
    llm, _ = agent_llm({**GOOD, "valuation": error})
    with pytest.raises(type(error)):
        run_committee(application(), llm=llm)