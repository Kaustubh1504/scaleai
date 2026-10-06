END = "<|end|>"


def render(messages, parts=None):
    """Chat-template text for one example; every assistant turn is closed with <|end|>."""
    parts = [] if parts is None else parts
    for m in messages:
        parts.append(f"<|{m.role}|>\n{m.content}\n")
        if m.role == "assistant":
            parts.append(END + "\n")
    return "".join(parts)
