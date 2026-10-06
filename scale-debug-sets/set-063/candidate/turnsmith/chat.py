"""Turn raw rows into an alternating user/assistant message list."""
from __future__ import annotations

ROLE_MAP = {"user": "user", "human": "user", "assistant": "assistant", "gpt": "assistant", "bot": "assistant"}


def to_messages(turns: list[dict]) -> list[dict]:
    messages: list[dict] = []
    for t in turns:
        role = ROLE_MAP.get(t["role"])
        if role is None or not t["text"]:
            continue
        if messages and messages[-1]["role"] == role:
            messages[-1]["content"] += "\n" + t["text"]
        else:
            messages.append({"role": role, "content": t["text"]})
    while messages and messages[0]["role"] != "user":
        messages.pop(0)
    while messages and messages[-1]["role"] != "assistant":
        messages.pop()
    return messages
