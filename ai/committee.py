from __future__ import annotations

from datetime import UTC, datetime

from agents import affordability, strategist, valuation
from agents.base import LLM
from common.enums import Agent
from llm.client import complete


def market_research_placeholder() -> dict:
    return {
        "agent": str(Agent.MARKET_RESEARCH),
        "model": "none",
        "output": {},
        "reasoning": "Market & Macro Researcher arrives in US-413 (Sprint 3).",
        "verdict": None,
        "stub": True,
        "timestamp": datetime.now(UTC).isoformat(),
    }


def run_committee(application: dict, *, llm: LLM = complete) -> dict:
    steps = [
        affordability.assess(application, llm=llm),
        valuation.assess(application, llm=llm),
        market_research_placeholder(),
    ]
    final = strategist.assess(steps, llm=llm)
    steps.append(final)
    return {
        "decision": final["output"]["decision"],
        "creditMemo": final["output"]["creditMemo"],
        "isStub": False,
        "steps": steps,
    }


if __name__ == "__main__":
    import json

    from common.tests import backend_dict

    application = backend_dict(valuation={"estimate": 380000, "low": 360000,
                                          "high": 400000, "modelVersion": "gbr-1"})
    result = run_committee(application)
    print(result["creditMemo"])
    print()
    print(json.dumps(result, indent=2))