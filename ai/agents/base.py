from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime

from llm.client import LLMResult

ATTEMPTS = 2

LLM = Callable[..., LLMResult]
Parser = Callable[[str], dict]


class AgentError(RuntimeError):
    """The model answered, but not with something the agent can use."""


def parse_json_object(text: str) -> dict:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise AgentError(f"answer is not valid JSON ({e.msg})") from None
    if not isinstance(data, dict):
        raise AgentError("answer must be a JSON object")
    return data


def ask_json(llm: LLM, agent: str, system: str, user: str,
             parse: Parser) -> tuple[LLMResult, dict]:
    problem = ""
    for _ in range(ATTEMPTS):
        prompt = user if not problem else (
            f"{user}\n\nYour previous answer was rejected: {problem}. "
            "Reply again with only the JSON object described in the instructions.")
        result = llm(agent, system, prompt, json_mode=True)
        try:
            return result, parse(result.text)
        except AgentError as e:
            problem = str(e)
    raise AgentError(f"{agent}: no valid answer after {ATTEMPTS} tries ({problem})")


def make_step(agent: str, result: LLMResult, prompt_version: str, facts: dict,
              output: dict, reasoning: str, verdict: str) -> dict:
    return {
        "agent": str(agent),
        "model": result.model,
        "provider": result.provider,
        "promptVersion": prompt_version,
        "input": facts,
        "output": output,
        "reasoning": reasoning,
        "verdict": verdict,
        "latencyS": result.latency_s,
        "timestamp": datetime.now(UTC).isoformat(),
    }
