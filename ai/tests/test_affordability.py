import json
from datetime import datetime, timedelta

import pytest

from agents.affordability import (PROMPT_VERSION, apply_floor, assess, build_facts,
                                  parse_answer, verdict_floor)
from agents.base import AgentError
from common.enums import Agent
from common.tests import backend_dict
from llm.client import LLMError, LLMResult

GOOD = {"verdict": "affordable", "summary": "Repayments are comfortable.",
        "strengths": ["LTI below the cap"], "concerns": []}


def fake_llm(*answers):
    """Stands in for llm.client.complete. Each call returns the next answer (a dict is sent
    as JSON, a str as is, an exception is raised). Returns (llm, list of the calls)."""
    queue = list(answers)
    calls = []

    def llm(agent, system, user, json_mode=False):
        calls.append({"agent": agent, "system": system, "user": user, "json_mode": json_mode})
        answer = queue.pop(0)
        if isinstance(answer, Exception):
            raise answer
        text = answer if isinstance(answer, str) else json.dumps(answer)
        return LLMResult(text=text, model="fake-model", provider="fake", latency_s=0.1)

    return llm, calls


def low_income_application():
    app = backend_dict()
    app["financials"]["grossAnnualIncome"] = 40_000
    return app


def test_facts_come_from_calc():
    facts = build_facts(backend_dict())
    assert facts["lti"] == 3.5263
    assert facts["ltiCap"] == 4.0
    assert facts["monthlyRepayment"] == 1599.34
    assert facts["stressedRepayment"] == 2008.49
    assert facts["monthlySurplusGross"] == 6017.33
    assert facts["maxLoan"] == 380000.0
    assert facts["limitedBy"] == "lti"
    assert facts["checks"] == {"ltiOk": True, "dtiOk": True, "stressedDtiOk": True}


def test_prompt_carries_the_figures_and_asks_for_json():
    llm, calls = fake_llm(GOOD)
    assess(backend_dict(), llm=llm)
    call = calls[0]
    assert call["agent"] == Agent.AFFORDABILITY
    assert call["json_mode"] is True
    assert '"lti": 3.5263' in call["user"]
    assert "Never calculate" in call["system"]


def test_numbers_from_the_model_are_ignored():
    llm, _ = fake_llm({**GOOD, "lti": 1.0, "monthlyRepayment": 1})
    step = assess(backend_dict(), llm=llm)
    assert step["input"]["lti"] == 3.5263
    assert "lti" not in step["output"]
    assert "monthlyRepayment" not in step["output"]


def test_step_matches_the_backend_contract():
    llm, _ = fake_llm(GOOD)
    step = assess(backend_dict(), llm=llm)
    for field, typ in {"agent": str, "model": str, "output": dict, "reasoning": str,
                       "timestamp": str}.items():
        assert isinstance(step[field], typ), field
    assert step["agent"] == "affordability"
    assert step["model"] == "fake-model"
    assert step["promptVersion"] == PROMPT_VERSION
    assert step["reasoning"] == "Repayments are comfortable."
    assert datetime.fromisoformat(step["timestamp"]).utcoffset() == timedelta(0)


def test_llm_errors_are_not_swallowed():
    llm, _ = fake_llm(LLMError("affordability", "groq", "rate limit reached (HTTP 429)"))
    with pytest.raises(LLMError):
        assess(backend_dict(), llm=llm)


@pytest.mark.parametrize("checks, floor", [
    ({"ltiOk": True, "dtiOk": True, "stressedDtiOk": True}, "affordable"),
    ({"ltiOk": True, "dtiOk": True, "stressedDtiOk": False}, "borderline"),
    ({"ltiOk": False, "dtiOk": True, "stressedDtiOk": True}, "unaffordable"),
    ({"ltiOk": True, "dtiOk": False, "stressedDtiOk": False}, "unaffordable"),
])
def test_verdict_floor(checks, floor):
    assert verdict_floor(checks) == floor


def test_apply_floor_keeps_the_stricter_verdict():
    assert apply_floor("affordable", "borderline") == "borderline"
    assert apply_floor("unaffordable", "affordable") == "unaffordable"


def test_model_cannot_approve_what_the_rules_decline():
    llm, _ = fake_llm(GOOD)
    step = assess(low_income_application(), llm=llm)
    assert step["verdict"] == "unaffordable"
    assert step["output"]["modelVerdict"] == "affordable"
    assert step["output"]["verdictOverridden"] is True


def test_model_may_be_stricter_than_the_rules():
    llm, _ = fake_llm({**GOOD, "verdict": "borderline"})
    step = assess(backend_dict(), llm=llm)
    assert step["verdict"] == "borderline"
    assert step["output"]["verdictOverridden"] is False


def test_invalid_answer_is_asked_again_with_the_reason():
    llm, calls = fake_llm("Sure! Here is my analysis...", GOOD)
    step = assess(backend_dict(), llm=llm)
    assert step["verdict"] == "affordable"
    assert len(calls) == 2
    assert "rejected: answer is not valid JSON" in calls[1]["user"]


def test_two_invalid_answers_raise():
    llm, _ = fake_llm("not json", {"verdict": "maybe", "summary": "?"})
    with pytest.raises(AgentError, match="no valid answer after 2 tries"):
        assess(backend_dict(), llm=llm)


@pytest.mark.parametrize("answer, problem", [
    ('["a list"]', "JSON object"),
    ('{"verdict": "approve", "summary": "x"}', "verdict must be one of"),
    ('{"verdict": "affordable", "summary": "  "}', "summary"),
    ('{"verdict": "affordable", "summary": "x", "concerns": "one string"}', "concerns"),
])
def test_parse_answer_rejects_bad_format(answer, problem):
    with pytest.raises(AgentError, match=problem):
        parse_answer(answer)


def test_parse_answer_drops_extra_keys_and_fills_missing_lists():
    answer = parse_answer('{"verdict": "borderline", "summary": " ok ", "score": 7}')
    assert answer == {"verdict": "borderline", "summary": "ok", "strengths": [], "concerns": []}
