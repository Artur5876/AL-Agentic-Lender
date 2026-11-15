from __future__ import annotations

import json

from agents.base import LLM, AgentError, ask_json, make_step, parse_json_object
from common.enums import Agent
from llm.client import complete

PROMPT_VERSION = "strategist-v1"
DECISIONS = ("approve", "conditionally_approve", "decline")

CLEAN = {"affordable", "acceptable"}
RED = {"unaffordable", "unacceptable"}

AGENT_NAMES = {
    "affordability": "Affordability",
    "valuation": "Valuation",
    "market_research": "Market research",
}

SYSTEM_PROMPT = """\
You are the Underwriting Strategist on a mortgage underwriting committee in Ireland.
The other agents have already assessed the application. Read their findings and recommend
a decision to the human underwriter. Do not calculate or change any number.

Decision:
- "decline" if any verdict is "unaffordable" or "unacceptable".
- "conditionally_approve" if any verdict is "borderline" or "caution". List the conditions
  the underwriter should check or require before approving.
- "approve" only if every available verdict is "affordable" or "acceptable".
An agent with "available": false gave no finding; mention it only if it matters.

Reply with one JSON object and nothing else:
{"decision": "approve" | "conditionally_approve" | "decline",
 "memo": "one paragraph for the underwriter that explains the decision",
 "conditions": ["condition", ...]}
"""


def build_facts(steps: list[dict]) -> dict:
    findings = {}
    for step in steps:
        findings[step["agent"]] = {
            "available": not step.get("stub", False),
            "verdict": step.get("verdict"),
            "summary": step["reasoning"],
            "concerns": step["output"].get("concerns", []),
            "flags": step["output"].get("flags", {}),
            "checks": step.get("input", {}).get("checks", {}),
        }
    return findings


def parse_answer(text: str) -> dict:
    data = parse_json_object(text)

    decision = data.get("decision")
    if decision not in DECISIONS:
        raise AgentError(f"decision must be one of {', '.join(DECISIONS)}, got {decision!r}")

    memo = data.get("memo")
    if not isinstance(memo, str) or not memo.strip():
        raise AgentError("memo must be a non-empty string")

    conditions = data.get("conditions", [])
    if not isinstance(conditions, list) or not all(isinstance(c, str) for c in conditions):
        raise AgentError("conditions must be a list of strings")

    return {"decision": decision, "memo": memo.strip(),
            "conditions": [c.strip() for c in conditions if c.strip()]}


def decision_floor(findings: dict) -> str:
    verdicts = [f["verdict"] for f in findings.values() if f["available"]]
    if any(v in RED for v in verdicts):
        return "decline"
    if not verdicts or any(v not in CLEAN for v in verdicts):  # amber, or unknown
        return "conditionally_approve"
    return "approve"


def apply_floor(decision: str, floor: str) -> str:
    return max(decision, floor, key=DECISIONS.index)


def default_conditions(findings: dict) -> list[str]:
    conditions = [f"Review the {AGENT_NAMES.get(agent, agent)} finding ({f['verdict']})."
                  for agent, f in findings.items()
                  if f["available"] and f["verdict"] not in CLEAN | RED]
    return conditions or ["Manual review of the full file by the underwriter."]


def credit_memo(decision: str, memo: str, conditions: list[str], steps: list[dict]) -> str:
    lines = [f"Recommendation: {decision.replace('_', ' ')}.", "", memo, "",
             "Committee findings:"]
    for step in steps:
        name = AGENT_NAMES.get(step["agent"], step["agent"])
        if step.get("stub"):
            lines.append(f"- {name}: not available ({step['reasoning']})")
        else:
            lines.append(f"- {name} ({step['model']}): {step['verdict']}. {step['reasoning']}")
    if conditions:
        lines += ["", "Conditions:"] + [f"- {c}" for c in conditions]
    return "\n".join(lines)


def assess(steps: list[dict], *, llm: LLM = complete) -> dict:
    findings = build_facts(steps)
    user = "Findings of the other agents:\n" + json.dumps(findings, indent=2)
    result, answer = ask_json(llm, Agent.UNDERWRITING_STRATEGIST, SYSTEM_PROMPT, user,
                              parse_answer)

    decision = apply_floor(answer["decision"], decision_floor(findings))
    conditions = answer["conditions"] if decision == "conditionally_approve" else []
    if decision == "conditionally_approve" and not conditions:
        conditions = default_conditions(findings)

    output = {
        "decision": decision,
        "modelDecision": answer["decision"],
        "decisionOverridden": decision != answer["decision"],
        "conditions": conditions,
        "creditMemo": credit_memo(decision, answer["memo"], conditions, steps),
    }
    return make_step(Agent.UNDERWRITING_STRATEGIST, result, PROMPT_VERSION, findings, output,
                     reasoning=answer["memo"], verdict=decision)
