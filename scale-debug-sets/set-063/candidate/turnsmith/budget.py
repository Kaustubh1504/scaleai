"""Token budget: estimate sizes and drop the oldest exchanges to fit."""
from __future__ import annotations

MESSAGE_OVERHEAD = 4


# VERIFIED
def count_tokens(messages: list[dict]) -> int:
    return sum(len(m["content"].split()) + MESSAGE_OVERHEAD for m in messages)


def fit_to_budget(system: dict, body: list[dict], max_tokens: int):
    """Return (body, dropped) that fits with the system message, or None."""
    dropped = 0
    while count_tokens([system] + body) > max_tokens:
        if len(body) <= 2:
            return None
        body = body[1:]
        dropped += 2
    return body, dropped
