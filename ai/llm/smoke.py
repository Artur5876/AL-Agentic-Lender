from __future__ import annotations

import sys

from llm.client import LLMError, complete
from llm.config import get_config

SYSTEM = "You are a health check. Reply only with JSON."
USER = "Return a JSON object with key ok set to true."


def main() -> int:
    config = get_config()
    failed = 0
    for agent, spec in config.items():
        label = f"{agent:<24} {spec.provider.name:<7} {spec.model:<22}"
        try:
            result = complete(agent, SYSTEM, USER, json_mode=True)
        except LLMError as e:
            failed += 1
            print(f"FAIL {label} {e.reason[:90]}")
        else:
            print(f"OK   {label} {result.latency_s:6.2f} s  {result.text.strip()[:40]}")

    providers = sorted({spec.provider.name + (" (local)" if spec.provider.local else "")
                        for spec in config.values()})
    print(f"\n{len(config) - failed}/{len(config)} agents answered; providers: "
          + ", ".join(providers))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())