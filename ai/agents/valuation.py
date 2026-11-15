from __future__ import annotations

import json

from agents.base import LLM, AgentError, ask_json, make_step, parse_json_object
from calc.metrics import MortgageCalculator
from common.app import Application
from common.enums import Agent
from llm.client import complete

PROMPT_VERSION = "valuation-v1"
VERDICTS = ("acceptable", "caution", "unacceptable")  # from best to worst

_calculator = MortgageCalculator()

SYSTEM_PROMPT = """\
You are the Valuation Agent on a mortgage underwriting committee in Ireland.
You check the property used as security for the loan. All figures were computed by the
bank's calculator and its valuation model. Do not calculate or change any number.

Fields:
- askingPrice: the price the borrower agreed to pay.
- estimate, estimateLow, estimateHigh: the bank's valuation of the property and its range.
  null means there is no valuation.
- differencePct: how far the asking price is above (+) or below (-) the estimate.
- overValued: true when the asking price is more than overvaluationThreshold above the
  estimate. null when there is no valuation.
- ltv: the loan divided by valueUsedForLtv (the lower of price and estimate).
  ltvOk says whether it is at or below maxLtv.

Verdict:
- "unacceptable" if ltvOk is false.
- "caution" if overValued is true or null.
- otherwise "acceptable". You may choose a stricter verdict if something else worries you.

Reply with one JSON object and nothing else:
{"verdict": "acceptable" | "caution" | "unacceptable",
 "summary": "2-3 sentences for the underwriter",
 "concerns": ["short point", ...]}
"""

def build_facts(application: dict) -> dict:
    """Every number and flag the agent may talk about, all from the calculation module."""
    c = _calculator
    app = Application.from_dict(application)
    valuation = application.get("valuation") or {}
    prop = application["property"]
    metrics = c.compute_metrics(app)

    facts = {
        "county": prop.get("county"),
        "propertyType": prop.get("propertyType"),
        "bedrooms": prop.get("bedrooms"),
        "floorAreaM2": prop.get("floorAreaM2"),
        "askingPrice": app.price,
        "estimate": app.estimate,
        "estimateLow": valuation.get("low"),
        "estimateHigh": valuation.get("high"),
        "valuationModel": valuation.get("modelVersion"),
        "differenceEur": None,
        "differencePct": None,
        "overValued": None,
        "overvaluationThreshold": c.limits.overvaluation_threshold,
        "loanAmount": app.loan_amount,
        "valueUsedForLtv": c.property_value(app.price, app.estimate),
        "ltv": metrics.ltv,
        "maxLtv": metrics.max_ltv,
        "ltvOk": metrics.is_ltv_ok(),
    }
    if app.estimate is not None:
        facts.update(c.price_vs_valuation(app.price, app.estimate))
    return facts

def parse_answer(text: str) -> dict:
    """Check the model's JSON against the fixed format. Extra keys are dropped."""
    data = parse_json_object(text)

    verdict = data.get("verdict")
    if verdict not in VERDICTS:
        raise AgentError(f"verdict must be one of {', '.join(VERDICTS)}, got {verdict!r}")

    summary = data.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        raise AgentError("summary must be a non-empty string")

    concerns = data.get("concerns", [])
    if not isinstance(concerns, list) or not all(isinstance(i, str) for i in concerns):
        raise AgentError("concerns must be a list of strings")

    return {"verdict": verdict, "summary": summary.strip(),
            "concerns": [i.strip() for i in concerns if i.strip()]}

def verdict_floor(facts: dict) -> str:
    if not facts["ltvOk"]:
        return "unacceptable"
    if facts["overValued"] is not False:
        return "caution"
    return "acceptable"


def apply_floor(verdict: str, floor: str) -> str:
    return max(verdict, floor, key=VERDICTS.index)

def assess(application: dict, *, llm: LLM = complete) -> dict:
    facts = build_facts(application)
    user = "Figures for this application:\n" + json.dumps(facts, indent=2)
    result, answer = ask_json(llm, Agent.VALUATION, SYSTEM_PROMPT, user, parse_answer)

    verdict = apply_floor(answer["verdict"], verdict_floor(facts))
    output = {
        "verdict": verdict,
        "modelVerdict": answer["verdict"],
        "verdictOverridden": verdict != answer["verdict"],
        "flags": {"overValued": facts["overValued"], "ltvOk": facts["ltvOk"]},
        "concerns": answer["concerns"],
    }
    return make_step(Agent.VALUATION, result, PROMPT_VERSION, facts, output,
                     reasoning=answer["summary"], verdict=verdict)


if __name__ == "__main__":
    from common.tests import backend_dict

    in_line = backend_dict(valuation={"estimate": 380000, "low": 360000, "high": 400000,
                                      "modelVersion": "gbr-1"})
    over = backend_dict(valuation={"estimate": 350000, "low": 330000, "high": 370000,
                                   "modelVersion": "gbr-1"})
    over["financials"] |= {"loanAmount": 300000, "deposit": 95000}
    for name, application in (("price in line", in_line), ("over-valued", over)):
        print(f"--- {name}")
        print(json.dumps(assess(application), indent=2))