from __future__ import annotations

import json

from agents.base import LLM, AgentError, ask_json, make_step, parse_json_object
from calc.metrics import MortgageCalculator
from common.app import Application
from common.enums import Agent
from llm.client import complete

PROMPT_VERSION = "affordability-v1"
VERDICTS = ("affordable", "borderline", "unaffordable")  # from best to worst

_calculator = MortgageCalculator()

SYSTEM_PROMPT = """\
You are the Affordability Agent on a mortgage underwriting committee in Ireland.
You receive figures already computed by the bank's calculator. Explain what they mean
for this borrower's ability to repay, for a human underwriter.

Rules:
- Use only the figures you are given. Never calculate, estimate or change a number.
- lti is loan-to-income; the Central Bank cap for this borrower is ltiCap.
- dti is the share of gross monthly income that goes on debts plus the mortgage;
  stressedDti is the same at the interest rate plus the stress buffer. Both must be
  at or below maxDti.
- monthlySurplusGross is gross income left after debts and the repayment, BEFORE tax.
  Treat it as an upper bound, not as money in hand.
- maxLoan is the most this borrower could borrow under the rules; limitedBy says which
  rule sets it.
- checks shows which lending rules pass. If ltiOk or dtiOk is false the verdict must be
  "unaffordable". If only stressedDtiOk is false it cannot be "affordable".

Reply with one JSON object and nothing else:
{"verdict": "affordable" | "borderline" | "unaffordable",
 "summary": "2-3 sentences for the underwriter",
 "strengths": ["short point", ...],
 "concerns": ["short point", ...]}
"""

def build_facts(application: dict) -> dict:
    c = _calculator
    app = Application.from_dict(application)
    metrics = c.compute_metrics(app)
    stressed = c.stressed_repayment(app.loan_amount, app.years)
    cap = c.max_loan(app.income, app.deposit, app.buyer_type)
    checks = metrics.to_dict()["checks"]
    return {
        "buyerType": str(app.buyer_type),
        "loanAmount": app.loan_amount,
        "grossAnnualIncome": app.income,
        "monthlyDebts": app.monthly_debts,
        "termYears": app.years,
        "lti": metrics.lti,
        "ltiCap": metrics.lti_cap,
        "dti": metrics.dti,
        "stressedDti": metrics.stressed_dti,
        "maxDti": metrics.max_dti,
        "monthlyRepayment": metrics.monthly_repayment,
        "stressedRepayment": stressed,
        "monthlySurplusGross": c.monthly_surplus(app.income, app.monthly_debts,
                                                 metrics.monthly_repayment),
        "stressedSurplusGross": c.monthly_surplus(app.income, app.monthly_debts, stressed),
        "maxLoan": cap["maxLoan"],
        "limitedBy": str(cap["limitedBy"]),
        "checks": {key: checks[key] for key in ("ltiOk", "dtiOk", "stressedDtiOk")},
    }


def parse_answer(text: str) -> dict:
    data = parse_json_object(text)

    verdict = data.get("verdict")
    if verdict not in VERDICTS:
        raise AgentError(f"verdict must be one of {', '.join(VERDICTS)}, got {verdict!r}")

    summary = data.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        raise AgentError("summary must be a non-empty string")

    answer = {"verdict": verdict, "summary": summary.strip()}
    for key in ("strengths", "concerns"):
        items = data.get(key, [])
        if not isinstance(items, list) or not all(isinstance(i, str) for i in items):
            raise AgentError(f"{key} must be a list of strings")
        answer[key] = [i.strip() for i in items if i.strip()]
    return answer


def verdict_floor(checks: dict) -> str:
    if not (checks["ltiOk"] and checks["dtiOk"]):
        return "unaffordable"
    if not checks["stressedDtiOk"]:
        return "borderline"
    return "affordable"


def apply_floor(verdict: str, floor: str) -> str:
    return max(verdict, floor, key=VERDICTS.index)

def assess(application: dict, *, llm: LLM = complete) -> dict:
    facts = build_facts(application)
    user = "Figures for this application:\n" + json.dumps(facts, indent=2)
    result, answer = ask_json(llm, Agent.AFFORDABILITY, SYSTEM_PROMPT, user, parse_answer)

    verdict = apply_floor(answer["verdict"], verdict_floor(facts["checks"]))
    output = {
        "verdict": verdict,
        "modelVerdict": answer["verdict"],
        "verdictOverridden": verdict != answer["verdict"],
        "strengths": answer["strengths"],
        "concerns": answer["concerns"],
    }
    return make_step(Agent.AFFORDABILITY, result, PROMPT_VERSION, facts, output,
                     reasoning=answer["summary"], verdict=verdict)


if __name__ == "__main__":  # one real run:  python -m agents.affordability
    from common.tests import backend_dict

    print(json.dumps(assess(backend_dict()), indent=2))