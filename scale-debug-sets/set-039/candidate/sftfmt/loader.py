import json

from .models import Conversation, Message, Role, normalize_role

DEFAULT_SYSTEM = "You are a helpful assistant."


def load_config(path):
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    return {"max_tokens": int(raw["max_tokens"]), "default_system": raw.get("default_system", DEFAULT_SYSTEM).strip()}


def load_conversations(path):
    conversations = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            raw = json.loads(line)
            messages = [Message(normalize_role(m.get("role")), (m.get("content") or "").strip())
                        for m in raw.get("messages", [])]
            messages = [m for m in messages if m.content]
            conversations.append(Conversation(raw["id"].strip().lower(), messages))
    return conversations


def validate(messages):
    """Return a rejection reason, or None if the turn order is usable."""
    body = messages[1:] if messages and messages[0].role is Role.SYSTEM else messages
    if not any(m.role is Role.ASSISTANT for m in body):
        return "no_assistant"
    expected = [Role.USER, Role.ASSISTANT]
    for i, m in enumerate(body):
        if m.role is not expected[i % 2]:
            return "bad_turn_order"
    if body[-1].role is not Role.ASSISTANT:
        return "bad_turn_order"
    return None


def with_system(messages, default_system):
    if messages and messages[0].role is Role.SYSTEM:
        return list(messages)
    return [Message(Role.SYSTEM, default_system)] + list(messages)
