from .models import Role

END = "<|end|>\n"


def tag(message):
    return f"<|{message.role.value}|>"


def block(message):
    return f"{tag(message)}\n{message.content}{END}"


def count_tokens(message):
    """Whitespace words plus one token each for the role tag and the end marker."""
    return len(message.content.split()) + 2


def total_tokens(messages):
    return sum(count_tokens(m) for m in messages)


# VERIFIED
def fits(messages, budget):
    return total_tokens(messages) <= budget


def truncate(messages, budget):
    """Drop the oldest user/assistant pair (after the system prompt) until it fits.

    Always keeps the system prompt and the final pair. Returns None if that is
    still over budget.
    """
    kept = list(messages)
    start = 1 if kept and kept[0].role is Role.SYSTEM else 0
    while not fits(kept, budget) and len(kept) - start > 2:
        del kept[start:start + 2]
    return kept if fits(kept, budget) else None


def render(messages):
    return "".join(block(m) for m in messages)
