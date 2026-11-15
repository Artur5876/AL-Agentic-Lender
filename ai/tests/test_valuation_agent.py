from datetime import datetime, timedelta

import pytest

from agents.base import AgentError
from agents.valuation import PROMPT_VERSION, assess, build_facts, parse_answer, verdict_floor
from common.enums import Agent
from common.tests import backend_dict
from tests.fakes import fake_llm

ACCEPTABLE = {"verdict": "acceptable", "summary": "Price is in line with the valuation.",
              "concerns": []}


def with_valuation(estimate, loan=335_000):
    app = backend_dict(valuation={"estimate": estimate, "low": estimate - 20_000,
                                  "high": estimate + 20_000, "modelVersion": "gbr-1"})
    app["financials"]["loanAmount"] = loan
    return app


IN_LINE = with_valuation(380_000)
OVER_VALUED = with_valuation(350_000, 300_000)
LTV_BREACH = with_valuation(340_000)


def test_facts_with_a_valuation():
    facts = build_facts(IN_LINE)
    assert facts["estimate"] == 380_000
    assert facts["differenceEur"] == 15_000
    assert facts["differencePct"] == 0.0395
    assert facts["overValued"] is False
    assert facts["valueUsedForLtv"] == 380_000
    assert facts["ltv"] == 0.8816
    assert facts["ltvOk"] is True
    assert facts["overvaluationThreshold"] == 0.1


def test_over_valued_is_flagged_by_calc():
    facts = build_facts(OVER_VALUED)
    assert facts["differencePct"] == 0.1286
    assert facts["overValued"] is True
    assert facts["ltvOk"] is True


def test_facts_without_a_valuation():
    facts = build_facts(backend_dict(valuation=None))
    assert facts["estimate"] is None
    assert facts["overValued"] is None
    assert facts["valueUsedForLtv"] == 395_000
    assert facts["ltv"] == 0.8481


def test_prompt_carries_the_figures_and_asks_for_json():
    llm, calls = fake_llm(ACCEPTABLE)
    assess(OVER_VALUED, llm=llm)
    call = calls[0]
    assert call["agent"] == Agent.VALUATION
    assert call["json_mode"] is True
    assert '"overValued": true' in call["user"]
    assert "Do not calculate" in call["system"]


def test_numbers_from_the_model_are_ignored():
    llm, _ = fake_llm({**ACCEPTABLE, "ltv": 0.5, "estimate": 999_999})
    step = assess(IN_LINE, llm=llm)
    assert step["input"]["ltv"] == 0.8816
    assert "ltv" not in step["output"] and "estimate" not in step["output"]


def test_step_matches_the_backend_contract():
    llm, _ = fake_llm(ACCEPTABLE)
    step = assess(IN_LINE, llm=llm)
    for field, typ in {"agent": str, "model": str, "output": dict, "reasoning": str,
                       "timestamp": str}.items():
        assert isinstance(step[field], typ), field
    assert step["agent"] == "valuation"
    assert step["promptVersion"] == PROMPT_VERSION
    assert step["output"]["flags"] == {"overValued": False, "ltvOk": True}
    assert datetime.fromisoformat(step["timestamp"]).utcoffset() == timedelta(0)


@pytest.mark.parametrize("over_valued, ltv_ok, floor", [
    (False, True, "acceptable"),
    (True, True, "caution"),
    (None, True, "caution"),  # no valuation to compare with
    (False, False, "unacceptable"),
    (True, False, "unacceptable"),
])
def test_verdict_floor(over_valued, ltv_ok, floor):
    assert verdict_floor({"overValued": over_valued, "ltvOk": ltv_ok}) == floor


def test_model_cannot_wave_through_an_over_valued_price():
    llm, _ = fake_llm(ACCEPTABLE)
    step = assess(OVER_VALUED, llm=llm)
    assert step["verdict"] == "caution"
    assert step["output"]["verdictOverridden"] is True
    assert step["output"]["flags"]["overValued"] is True


def test_model_cannot_ignore_an_ltv_breach():
    llm, _ = fake_llm({**ACCEPTABLE, "verdict": "caution"})
    step = assess(LTV_BREACH, llm=llm)
    assert step["verdict"] == "unacceptable"
    assert step["output"]["modelVerdict"] == "caution"


def test_no_valuation_is_at_best_caution():
    llm, _ = fake_llm(ACCEPTABLE)
    assert assess(backend_dict(valuation=None), llm=llm)["verdict"] == "caution"


def test_model_may_be_stricter():
    llm, _ = fake_llm({**ACCEPTABLE, "verdict": "caution"})
    step = assess(IN_LINE, llm=llm)
    assert step["verdict"] == "caution"
    assert step["output"]["verdictOverridden"] is False


def test_invalid_answer_is_asked_again():
    llm, calls = fake_llm("The property looks fine.", ACCEPTABLE)
    assert assess(IN_LINE, llm=llm)["verdict"] == "acceptable"
    assert len(calls) == 2


@pytest.mark.parametrize("answer, problem", [
    ('{"verdict": "affordable", "summary": "x"}', "verdict must be one of"),
    ('{"verdict": "caution", "summary": ""}', "summary"),
    ('{"verdict": "caution", "summary": "x", "concerns": [1, 2]}', "concerns"),
])
def test_parse_answer_rejects_bad_format(answer, problem):
    with pytest.raises(AgentError, match=problem):
        parse_answer(answer)
