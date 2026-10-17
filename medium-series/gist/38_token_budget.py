# 38. Token budget and cost tracking for LLM calls
# Standalone: copy this file as-is. Deps: stdlib

import threading


def new_budget(limit_tokens: int) -> dict:
    return {"limit": limit_tokens, "used": 0, "reserved": 0, "calls": 0,
            "prompt": 0, "completion": 0, "lock": threading.Lock()}


def estimate_tokens(*texts: str) -> int:
    """Rough upper-bound estimate (~4 chars per token) for reserving budget before a call."""
    return sum(len(t) for t in texts) // 4 + 1


def reserve(budget: dict, estimate: int) -> bool:
    """Reserve before calling. False -> over budget: skip the call (mark the row budget_exceeded)."""
    with budget["lock"]:
        if budget["used"] + budget["reserved"] + estimate > budget["limit"]:
            return False
        budget["reserved"] += estimate
        return True


def settle(budget: dict, estimate: int, usage=None) -> None:
    """After the call: release the reservation and record real usage (OpenAI's response["usage"])."""
    usage = usage or {}
    with budget["lock"]:
        budget["reserved"] -= estimate
        budget["used"] += usage.get("total_tokens", estimate)
        budget["prompt"] += usage.get("prompt_tokens", 0)
        budget["completion"] += usage.get("completion_tokens", 0)
        budget["calls"] += 1


def cost_usd(budget: dict, input_per_million: float, output_per_million: float) -> float:
    return round(budget["prompt"] * input_per_million / 1e6
                 + budget["completion"] * output_per_million / 1e6, 6)
