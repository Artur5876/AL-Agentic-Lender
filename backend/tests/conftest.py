import functools
import json
import os

import committee
import pytest
from llm.client import LLMResult

os.environ["AL_COMMITTEE_MODE"] = "stub"

FAKE_ANSWERS = {
    "affordability": {"verdict": "affordable", "summary": "Repayments are comfortable.",
                      "strengths": ["LTI below the cap"], "concerns": []},
    "valuation": {"verdict": "acceptable", "summary": "No valuation to compare with.",
                  "concerns": ["No independent valuation"]},
    "underwriting_strategist": {"decision": "approve", "memo": "Fine apart from the valuation.",
                                "conditions": []},
}


def fake_llm(agent, system, user, json_mode=False):
    """Stands in for llm.client.complete; the model name says which agent asked."""
    agent = str(agent)
    return LLMResult(text=json.dumps(FAKE_ANSWERS[agent]), model=f"fake-{agent}",
                     provider="fake", latency_s=0.1)


@pytest.fixture
def ai_committee():
    return functools.partial(committee.run_committee, llm=fake_llm)