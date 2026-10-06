END = "<|end|>"


def render(messages, parts=[]):
    """Chat-template text for one example; every assistant turn is closed with <|end|>."""
    for m in messages:
        parts.append(f"<|{m.role}|>\n{m.content}\n")
        if m.role == "assistant":
            parts.append(END + "\n")
    return "".join(parts)
