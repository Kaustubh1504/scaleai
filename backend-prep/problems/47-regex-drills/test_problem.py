def test_tickets_basic(sol):
    """find_tickets returns refs once each, in order of first appearance"""
    assert sol.find_tickets("See TKT-12 and TKT-9, dup TKT-12. (TKT-100000)") == ["TKT-12", "TKT-9", "TKT-100000"]


def test_tickets_word_boundaries(sol):
    """find_tickets ignores XTKT-1, TKT-1234567, lower-case tkt-5 and a bare TKT-"""
    text = "XTKT-1 TKT-1234567 tkt-5 TKT- TKT-77x TKT-42"
    assert sol.find_tickets(text) == ["TKT-42"]
    assert sol.find_tickets("") == []


def test_emails(sol):
    """find_emails lower-cases, de-duplicates and drops a sentence-ending period"""
    text = "Mail Bob@Example.com or ann.lee+qa@x.co.uk. Also bob@example.com, not me@localhost."
    assert sol.find_emails(text) == ["bob@example.com", "ann.lee+qa@x.co.uk"], \
        "if you got tuples or only domain parts, your pattern has a capturing group"


def test_idempotency_keys_valid(sol):
    """is_valid_idempotency_key accepts 1-64 chars of [A-Za-z0-9_-]"""
    for key in ["a", "order-42_retry", "X" * 64, "0123-abcd_EF"]:
        assert sol.is_valid_idempotency_key(key) is True, f"{key!r} should be valid"


def test_idempotency_keys_invalid(sol):
    """is_valid_idempotency_key rejects empty, 65 chars, spaces, a trailing newline and non-strings"""
    for key in ["", "X" * 65, "has space", "abc\n", "semi;colon", "ünï", None, 42]:
        assert sol.is_valid_idempotency_key(key) is False, f"{key!r} should be invalid (use fullmatch)"


def test_parse_log_line(sol):
    """parse_log_line returns typed fields from a valid line (trailing newline ok)"""
    got = sol.parse_log_line("2024-05-01T12:00:03Z POST /v1/tasks/t_19/labels 201 35ms req=ab12-x\n")
    assert got == {"ts": "2024-05-01T12:00:03Z", "method": "POST", "path": "/v1/tasks/t_19/labels",
                   "status": 201, "latency_ms": 35, "request_id": "ab12-x"}


def test_parse_log_line_bad(sol):
    """parse_log_line returns None for malformed lines"""
    bad = [
        "",
        "garbage",
        "2024-05-01T12:00:03Z FETCH /v1/x 200 3ms req=a",      # bad method
        "2024-05-01T12:00:03Z GET v1/x 200 3ms req=a",         # path without /
        "2024-05-01T12:00:03Z GET /v1/x 20 3ms req=a",         # 2-digit status
        "2024-05-01T12:00:03Z GET /v1/x 200 3.5ms req=a",      # non-int latency
        "2024-05-01T12:00:03Z GET /v1/x 200 3ms",              # missing req
        "2024-05-01T12:00:03Z GET /v1/x 200 3ms req=a extra",  # trailing junk
    ]
    for line in bad:
        assert sol.parse_log_line(line) is None, f"{line!r} should not parse"


def test_redact_emails_and_phones(sol):
    """redact_pii replaces emails with [EMAIL] and each phone format with [PHONE]"""
    text = "call (415) 555-0123 or +1 415.555.0199 or 415-555-0100 or 415 555 0101, ann@x.io"
    assert sol.redact_pii(text) == "call [PHONE] or [PHONE] or [PHONE] or [PHONE], [EMAIL]"


def test_redact_leaves_non_pii(sol):
    """redact_pii leaves ticket refs, bare 10-digit ids and longer numbers alone"""
    text = "TKT-1234 order 4155550123 acct 1415-555-01234 v2.0.1"
    assert sol.redact_pii(text) == text
