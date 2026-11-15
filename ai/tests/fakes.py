import json

from llm.client import LLMResult


def fake_llm(*answers):
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


def agent_llm(answers: dict):
    calls = []

    def llm(agent, system, user, json_mode=False):
        calls.append(str(agent))
        answer = answers[str(agent)]
        if isinstance(answer, Exception):
            raise answer
        text = answer if isinstance(answer, str) else json.dumps(answer)
        return LLMResult(text=text, model=f"fake-{agent}", provider="fake", latency_s=0.1)

    return llm, calls
