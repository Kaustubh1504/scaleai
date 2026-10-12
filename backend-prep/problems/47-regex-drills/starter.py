"""47. Regex drills

Template: imports, constants, exceptions and signatures are here.
Fill in every `raise NotImplementedError` (add your own helpers as needed)."""

from __future__ import annotations
import re

TICKET_RE = re.compile(r"\bTKT-\d{1,6}\b")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")
IDEMPOTENCY_KEY_RE = re.compile(r"[A-Za-z0-9_-]{1,64}")
LOG_RE = re.compile(
    r"(?P<ts>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z) "
    r"(?P<method>GET|POST|PUT|PATCH|DELETE) "
    r"(?P<path>/\S*) "
    r"(?P<status>\d{3}) "
    r"(?P<latency_ms>\d+)ms "
    r"req=(?P<request_id>[A-Za-z0-9-]+)"
)
PHONE_RE = re.compile(r"(?<!\d)(?:\+1[ -])?(?:\(\d{3}\)|\d{3})[ .-]\d{3}[ .-]\d{4}(?!\d)")


def find_tickets(text: str) -> list[str]:
    raise NotImplementedError


def find_emails(text: str) -> list[str]:
    raise NotImplementedError


def is_valid_idempotency_key(key: object) -> bool:
    raise NotImplementedError


def parse_log_line(line: str) -> dict | None:
    raise NotImplementedError


def redact_pii(text: str) -> str:
    raise NotImplementedError


if __name__ == "__main__":
    print(find_tickets("See TKT-12 and TKT-9, dup TKT-12"))
    print(find_emails("Mail Bob@Example.com or ann@x.co.uk."))
    print(is_valid_idempotency_key("order-42_retry"), is_valid_idempotency_key("abc\n"))
    print(parse_log_line("2024-05-01T12:00:03Z GET /v1/tasks/t_19 200 35ms req=ab12-x"))
    print(redact_pii("call (415) 555-0123 or +1 415.555.0199, ann@x.io"))
