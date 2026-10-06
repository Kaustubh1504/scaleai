from dataclasses import dataclass

from .loader import clean, norm_key

ROLES = ("system", "user", "assistant")


@dataclass(frozen=True)
class Turn:
    role: str
    content: str


def normalise_turns(raw_turns, aliases):
    """Map role aliases, trim content and drop turns the template can't use."""
    turns = []
    for item in raw_turns:
        role = norm_key(item.get("role"))
        role = aliases.get(role, role)
        content = clean(item.get("content"))
        if role not in ROLES or not content:
            continue
        # a system prompt only makes sense as the opening turn
        if role == "system" and turns:
            break
        turns.append(Turn(role, content))
    return turns


# VERIFIED
def merge_consecutive(turns):
    merged = []
    for turn in turns:
        if merged and merged[-1].role == turn.role:
            merged[-1] = Turn(turn.role, merged[-1].content + "\n" + turn.content)
        else:
            merged.append(turn)
    return merged


def split_pairs(turns):
    """Return (system turn or None, [(user, assistant), ...])."""
    system = turns[0] if turns and turns[0].role == "system" else None
    body = list(turns[1:] if system else turns)
    while body and body[0].role != "user":
        body.pop(0)
    while body and body[-1].role != "assistant":
        body.pop()
    pairs = [(body[i], body[i + 1]) for i in range(0, len(body) - 1, 2)]
    return system, pairs


def flatten(system, pairs):
    return ([system] if system else []) + [turn for pair in pairs for turn in pair]


def render(system, pairs):
    parts = [f"<|{turn.role}|>\n{turn.content}\n" for turn in flatten(system, pairs)]
    parts.append("<|end|>")
    return "".join(parts)
