from dataclasses import dataclass

ROLES = ("system", "user", "assistant")


@dataclass
class Message:
    role: str
    content: str


class Rejected(Exception):
    pass


def normalise_roles(messages, aliases):
    out = []
    for m in messages:
        role = m.role.strip().lower()
        role = aliases.get(role, role)
        if role not in ROLES:
            raise Rejected("unknown_role")
        if not m.content:
            raise Rejected("empty_message")
        out.append(Message(role, m.content))
    return out


def merge_consecutive(messages):
    merged = []
    for m in messages:
        if merged and merged[-1].role == m.role:
            merged[-1] = Message(m.role, merged[-1].content + "\n" + m.content)
        else:
            merged.append(m)
    return merged


def check_order(messages):
    body = messages
    if messages and messages[0].role == "system":
        body = messages[1:]
    if any(m.role == "system" for m in body):
        raise Rejected("misplaced_system")
    for i, m in enumerate(body):
        if m.role != ("user" if i % 2 == 0 else "assistant"):
            raise Rejected("bad_order")
    if not body or body[-1].role != "assistant":
        raise Rejected("bad_order")


def count_tokens(messages, overhead):
    return sum(len(m.content.split()) + overhead for m in messages)


# VERIFIED
def truncate(messages, max_tokens, overhead):
    """Drop the oldest user/assistant pairs (never the system prompt) until it fits."""
    system = messages[:1] if messages and messages[0].role == "system" else []
    body = messages[len(system):]
    dropped = 0
    while count_tokens(system + body, overhead) > max_tokens and len(body) > 2:
        body = body[2:]
        dropped += 1
    if count_tokens(system + body, overhead) > max_tokens:
        raise Rejected("too_long")
    return system + body, dropped
