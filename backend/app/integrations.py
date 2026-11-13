"""Connection points to the AI lead's code (ai/ folder). Core calls these; the AI lead owns them.

Keeping them here means the API contract (US-311) stays stable when the valuation model
(US-402/403) or the calculation module (US-410) changes.
"""

from __future__ import annotations

from functools import lru_cache

import joblib
from calc.metrics import MortgageCalculator
from common.app import Application
from common.enums import Buyer
from valuation.train import MODEL_PATH, predict

STUB_MODEL_VERSION = "stub-0"
_calculator = MortgageCalculator()


@lru_cache(maxsize=1)
def _load_model() -> dict | None:
    """Load the trained valuation model once; None if model.joblib is missing."""
    if not MODEL_PATH.exists():
        return None
    return joblib.load(MODEL_PATH)


def estimate_value(property_spec: dict) -> dict:
    """Valuation model (US-402 / US-403, AI lead). Falls back to the stub without a model."""
    bundle = _load_model()
    if bundle is None:
        return {
            "estimate": 380000.0,
            "low": 360000.0,
            "high": 400000.0,
            "modelVersion": STUB_MODEL_VERSION,
        }
    return predict(bundle, property_spec)

def compute_metrics(application: dict) -> dict:
    """Calculation module (US-410, AI lead): LTI, LTV, DTI, stressed DTI, repayment, checks."""
    return _calculator.compute_metrics(Application.from_dict(application)).to_dict()


def affordability(buyer_type: str, gross_annual_income: float, monthly_debts: float,
                  deposit: float, term_years: int) -> dict:
    """Borrowing estimate (US-111): the most this borrower could borrow, and its figures.

    Every figure comes from the calculation module (MortgageCalculator). The only step done
    here is the assumed purchase price for the LTV: max loan + deposit (the most the borrower
    could buy with that deposit). LTV is None when that price is 0 (no income and no deposit).
    """
    c = _calculator
    limit = c.max_loan(gross_annual_income, deposit, Buyer(buyer_type))
    loan = limit["maxLoan"]
    price = loan + deposit
    repayment = c.monthly_repayment(loan, c.limits.base_apr, term_years)
    return {
        "maxLoan": loan,
        "limitedBy": str(limit["limitedBy"]),
        "lti": c.lti(loan, gross_annual_income),
        "ltv": c.ltv(loan, price) if price > 0 else None,
        "monthlyRepayment": repayment,
        "dti": c.dti(monthly_debts, repayment, gross_annual_income),
    }


# ---------------------------------------------------------------------------
# AI underwriting committee (US-313 Core side, US-414 AI lead)
#
# Contract: run_committee(application: dict) -> dict with this shape
#   {
#     "decision":   "approve" | "conditionally_approve" | "decline",
#     "creditMemo": str,
#     "isStub":     bool,
#     "steps": [ {"agent", "model", "output" (dict), "reasoning" (str),
#                 "timestamp" (ISO 8601 UTC)} ]   one per agent in COMMITTEE_AGENTS
#   }
# The backend validates the result and saves it to Firestore. The committee itself
# never touches Firebase, and never does arithmetic: every figure comes from the
# calculation module (application["metrics"], filled by ai/calc at submission).
#
# SWITCH TO THE REAL COMMITTEE: once ai/committee.py provides the same function,
# add this one line directly below the stub function (it replaces the stub):
#     from committee import run_committee  # noqa: E402,F811  (ai/committee.py, US-414)
# ---------------------------------------------------------------------------

COMMITTEE_DECISIONS = frozenset({"approve", "conditionally_approve", "decline"})
COMMITTEE_AGENTS = ("affordability", "valuation", "market_research", "underwriting_strategist")
STEP_FIELDS = {"agent": str, "model": str, "output": dict, "reasoning": str, "timestamp": str}
STUB_COMMITTEE_MODEL = "stub-committee-0"


class CommitteeResultError(ValueError):
    """The committee returned something that does not match the contract above."""


def run_committee(application: dict) -> dict:
    """STUB committee (US-313) until the AI lead's agents (US-414) are connected.

    Copies figures from application["metrics"] (calc module) and decides from the
    calc module's own pass/fail checks. It calculates nothing itself. Output is
    marked isStub=True so the clients can label it as placeholder advice.
    """
    from datetime import UTC, datetime

    def ts() -> str:
        return datetime.now(UTC).isoformat()

    metrics = application.get("metrics") or {}
    checks = metrics.get("checks") or {}
    valuation = application.get("valuation") or {}
    prop = application.get("property") or {}

    if not checks:
        decision = "conditionally_approve"
        why = "No calculation-module metrics were available, so the file needs manual review."
    elif not (checks.get("ltiOk") and checks.get("ltvOk") and checks.get("dtiOk")):
        decision = "decline"
        failed = [k for k in ("ltiOk", "ltvOk", "dtiOk") if not checks.get(k)]
        why = f"Lending-rule checks failed: {', '.join(failed)}."
    elif not checks.get("stressedDtiOk"):
        decision = "conditionally_approve"
        why = "Passes LTI, LTV and DTI, but fails the stressed DTI check."
    else:
        decision = "approve"
        why = "Passes every calculation-module check (LTI, LTV, DTI, stressed DTI)."

    steps = [
        {
            "agent": "affordability",
            "model": STUB_COMMITTEE_MODEL,
            "output": {k: metrics.get(k) for k in ("lti", "dti", "stressedDti",
                                                   "monthlyRepayment")},
            "reasoning": f"Stub: copied LTI {metrics.get('lti')}, DTI {metrics.get('dti')}, "
                         f"stressed DTI {metrics.get('stressedDti')} from the calc module.",
            "timestamp": ts(),
        },
        {
            "agent": "valuation",
            "model": STUB_COMMITTEE_MODEL,
            "output": {"estimate": valuation.get("estimate"),
                       "modelVersion": valuation.get("modelVersion"),
                       "askingPrice": prop.get("askingPrice"),
                       "ltv": metrics.get("ltv")},
            "reasoning": "Stub: copied the stored valuation and the calc-module LTV.",
            "timestamp": ts(),
        },
        {
            "agent": "market_research",
            "model": STUB_COMMITTEE_MODEL,
            "output": {"county": prop.get("county"), "propertyType": prop.get("propertyType")},
            "reasoning": "Stub: no market research performed.",
            "timestamp": ts(),
        },
        {
            "agent": "underwriting_strategist",
            "model": STUB_COMMITTEE_MODEL,
            "output": {"decision": decision, "checks": checks},
            "reasoning": f"Stub: {why}",
            "timestamp": ts(),
        },
    ]
    return {
        "decision": decision,
        "creditMemo": f"[STUB - not real AI advice] {why}",
        "isStub": True,
        "steps": steps,
    }


def validate_committee_result(result: object) -> dict:
    """Return `result` unchanged if it matches the contract, else raise CommitteeResultError.

    Extra keys are allowed (the AI lead may add e.g. promptVersion or verdict to a step).
    """
    from datetime import datetime, timedelta

    if not isinstance(result, dict):
        raise CommitteeResultError("Committee result must be a dict.")
    if result.get("decision") not in COMMITTEE_DECISIONS:
        raise CommitteeResultError(f"Invalid decision: {result.get('decision')!r}.")
    if not isinstance(result.get("creditMemo"), str):
        raise CommitteeResultError("creditMemo must be a string.")
    if not isinstance(result.get("isStub"), bool):
        raise CommitteeResultError("isStub must be true or false.")
    steps = result.get("steps")
    if not isinstance(steps, list):
        raise CommitteeResultError("steps must be a list.")

    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            raise CommitteeResultError(f"steps[{i}] must be a dict.")
        for field, typ in STEP_FIELDS.items():
            if not isinstance(step.get(field), typ):
                raise CommitteeResultError(
                    f"steps[{i}].{field} is missing or not a {typ.__name__}.")
        try:
            at = datetime.fromisoformat(step["timestamp"].replace("Z", "+00:00"))
        except ValueError:
            raise CommitteeResultError(f"steps[{i}].timestamp is not ISO 8601.") from None
        if at.utcoffset() != timedelta(0):
            raise CommitteeResultError(f"steps[{i}].timestamp must be UTC.")

    agents = [s["agent"] for s in steps]
    if sorted(agents) != sorted(COMMITTEE_AGENTS):
        raise CommitteeResultError(
            f"steps must contain each agent exactly once: {', '.join(COMMITTEE_AGENTS)}; "
            f"got {agents}.")
    return result
