import json

from .loader import clean, parse_flag
from .models import Transition


def load_workflow(path):
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    return [
        Transition(
            source=clean(item["from"]).lower(),
            action=clean(item["action"]).lower(),
            target=clean(item["to"]).lower(),
            roles=frozenset(clean(r).lower() for r in item["roles"]),
            counts_as_response=parse_flag(item.get("counts_as_response", False)),
        )
        for item in raw
    ]


def find_transition(transitions, state, action, role):
    """The first transition out of `state` for `action` that `role` may take, or None."""
    for t in transitions:
        if t.source == state and t.action == action:
            if role in t.roles:
                return t
    return None


def has_transition(transitions, state, action):
    return any(t.source == state and t.action == action for t in transitions)
