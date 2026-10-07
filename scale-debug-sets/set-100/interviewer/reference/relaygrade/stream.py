import json
from dataclasses import dataclass

from .wire import EvalError


class StreamTruncated(EvalError):
    pass


@dataclass(frozen=True)
class Completion:
    text: str
    finish_reason: str
    tokens: int


def iter_events(body):
    """The completion stream is NDJSON: one JSON event per line."""
    for line in body.decode("utf-8").splitlines():
        if line.strip():
            yield json.loads(line)


def assemble(body):
    """Rebuild a completion from delta events.

    The relay can deliver deltas out of order and may resend a delta it is unsure
    was delivered; `seq` identifies each delta. The stream ends with a `done` event.
    """
    parts, seen = [], set()
    for event in iter_events(body):
        if event.get("done"):
            text = "".join(delta for _, delta in sorted(parts))
            return Completion(text, event["finish_reason"], event["usage"]["completion_tokens"])
        if event["seq"] in seen:
            continue
        seen.add(event["seq"])
        parts.append((event["seq"], event["delta"]))
    raise StreamTruncated("stream ended before done")
