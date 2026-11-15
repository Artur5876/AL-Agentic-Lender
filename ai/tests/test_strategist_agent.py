import pytest

from agents.base import AgentError
from agents.strategist import (DECISIONS, PROMPT_VERSION, assess, build_facts,
                               decision_floor, parse_answer)
from common.enums import Agent
from tests.fakes import fake_llm


def step(agent, verdict, *, stub=False, concerns=()):
    return {"agent": agent, "model": f"model-{agent}", "verdict": verdict, "stub": stub,
            "reasoning": f"{agent} summary.", "input": {},
            "output": {"concerns": list(concerns)}}


def steps(affordability="affordable", valuation="acceptable"):
    return [step("affordability", affordability),
            step("valuation", valuation, concerns=["Asking price 12.9 % over estimate"]),
            step("market_research", None, stub=True)]


APPROVE = {"decision": "approve", "memo": "Strong file.", "conditions": []}


def test_decisions_match_the_backend():
    assert set(DECISIONS) == {"approve", "conditionally_approve", "decline"}


@pytest.mark.parametrize("answer, problem", [
    ('{"decision": "approved", "memo": "x"}', "decision must be one of"),
    ('{"decision": "Approve", "memo": "x"}', "decision must be one of"),
    ('{"decision": "approve", "memo": ""}', "memo"),
    ('{"decision": "approve", "memo": "x", "conditions": "none"}', "conditions"),
])
def test_parse_answer_rejects_bad_format(answer, problem):
    with pytest.raises(AgentError, match=problem):
        parse_answer(answer)


@pytest.mark.parametrize("affordability, valuation, floor", [
    ("affordable", "acceptable", "approve"),
    ("borderline", "acceptable", "conditionally_approve"),
    ("affordable", "caution", "conditionally_approve"),
    ("unaffordable", "acceptable", "decline"),
    ("affordable", "unacceptable", "decline"),
    ("borderline", "unacceptable", "decline"),
])
def test_decision_floor(affordability, valuation, floor):
    assert decision_floor(build_facts(steps(affordability, valuation))) == floor


def test_unknown_verdict_needs_a_review():
    assert decision_floor(build_facts(steps(valuation="???"))) == "conditionally_approve"


def test_placeholder_agent_does_not_count():
    findings = build_facts(steps())
    assert findings["market_research"]["available"] is False
    assert decision_floor(findings) == "approve"


def test_model_cannot_approve_a_red_verdict():
    llm, _ = fake_llm(APPROVE)
    result = assess(steps(affordability="unaffordable"), llm=llm)
    assert result["output"]["decision"] == "decline"
    assert result["output"]["modelDecision"] == "approve"
    assert result["output"]["decisionOverridden"] is True
    assert result["output"]["conditions"] == []


def test_conditional_gets_default_conditions_when_the_model_gave_none():
    llm, _ = fake_llm(APPROVE)
    result = assess(steps(valuation="caution"), llm=llm)
    assert result["output"]["decision"] == "conditionally_approve"
    assert result["output"]["conditions"] == ["Review the Valuation finding (caution)."]


def test_model_conditions_are_kept():
    llm, _ = fake_llm({"decision": "conditionally_approve", "memo": "Check the price.",
                       "conditions": ["Independent valuation before drawdown"]})
    result = assess(steps(valuation="caution"), llm=llm)
    assert result["output"]["conditions"] == ["Independent valuation before drawdown"]


def test_model_may_be_stricter():
    llm, _ = fake_llm({"decision": "decline", "memo": "Too risky.", "conditions": []})
    result = assess(steps(), llm=llm)
    assert result["output"]["decision"] == "decline"
    assert result["output"]["decisionOverridden"] is False


def test_credit_memo_lists_every_agents_finding():
    llm, _ = fake_llm({**APPROVE, "memo": "My own paragraph."})
    memo = assess(steps(valuation="caution"), llm=llm)["output"]["creditMemo"]
    assert memo.startswith("Recommendation: conditionally approve.")
    assert "My own paragraph." in memo
    assert "- Affordability (model-affordability): affordable. affordability summary." in memo
    assert "- Valuation (model-valuation): caution. valuation summary." in memo
    assert "- Market research: not available" in memo
    assert "Conditions:\n- Review the Valuation finding (caution)." in memo


def test_prompt_carries_the_findings():
    llm, calls = fake_llm(APPROVE)
    assess(steps(valuation="caution"), llm=llm)
    call = calls[0]
    assert call["agent"] == Agent.UNDERWRITING_STRATEGIST
    assert call["json_mode"] is True
    assert '"verdict": "caution"' in call["user"]
    assert "Asking price 12.9 % over estimate" in call["user"]


def test_step_shape():
    llm, _ = fake_llm(APPROVE)
    result = assess(steps(), llm=llm)
    assert result["agent"] == "underwriting_strategist"
    assert result["promptVersion"] == PROMPT_VERSION
    assert result["verdict"] == result["output"]["decision"] == "approve"
    assert result["reasoning"] == "Strong file."
