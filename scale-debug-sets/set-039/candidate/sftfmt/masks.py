from .models import Role
from .render import block, tag


def assistant_spans(messages):
    """[start, end) character spans of assistant content inside render(messages)."""
    spans, offset = [], 0
    for message in messages:
        if message.role is Role.ASSISTANT:
            start = offset + len(tag(message))
            spans.append([start, start + len(message.content)])
        offset += len(block(message))
    return spans
