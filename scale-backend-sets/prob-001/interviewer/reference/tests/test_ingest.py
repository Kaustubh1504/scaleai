import pytest

from app.ingest import IngestError, ingest

HEADER = "ticket_id,customer_email,subject,body,created_at\n"


def csv_rows(*rows: str) -> bytes:
    return (HEADER + "\n".join(rows) + "\n").encode()


def test_valid_row_is_stripped():
    result = ingest(".csv", csv_rows(" T-1 , a@b.co , Hi , Body ,2024-01-01T00:00:00Z"))
    assert result.tickets == [{"ticket_id": "T-1", "customer_email": "a@b.co", "subject": "Hi", "body": "Body",
                               "created_at": "2024-01-01T00:00:00Z"}]
    assert result.errors == [] and result.total_rows == 1


@pytest.mark.parametrize(
    "row, field",
    [
        (",a@b.co,s,b,2024-01-01T00:00:00Z", "ticket_id"),
        ("T-1,nope,s,b,2024-01-01T00:00:00Z", "customer_email"),
        ("T-1,a@b,s,b,2024-01-01T00:00:00Z", "customer_email"),
        ("T-1,a@b.co, ,b,2024-01-01T00:00:00Z", "subject"),
        ("T-1,a@b.co,s,,2024-01-01T00:00:00Z", "body"),
        ("T-1,a@b.co,s,b,2024-02-30T00:00:00Z", "created_at"),
        ("T-1,a@b.co,s,b", None),
        ("T-1,a@b.co,s,b,2024-01-01T00:00:00Z,extra", None),
    ],
)
def test_invalid_rows(row, field):
    result = ingest(".csv", csv_rows(row))
    assert result.tickets == []
    assert [(e["row"], e["field"]) for e in result.errors] == [(1, field)]


def test_first_failing_rule_wins():
    result = ingest(".csv", csv_rows(",bad-email,,,nope"))
    assert result.errors[0]["field"] == "ticket_id"


def test_duplicates_only_count_valid_rows():
    result = ingest(".csv", csv_rows(
        "T-1,bad,s,b,2024-01-01T00:00:00Z",   # invalid, so T-1 is still free
        "T-1,a@b.co,s,b,2024-01-01T00:00:00Z",
        "T-1,c@d.co,s,b,2024-01-01T00:00:00Z",
    ))
    assert [t["customer_email"] for t in result.tickets] == ["a@b.co"]
    assert [(e["row"], e["field"]) for e in result.errors] == [(1, "customer_email"), (3, "ticket_id")]


def test_quoted_newlines_blank_lines_bom_and_column_order():
    raw = ("﻿body,created_at,subject,ticket_id,customer_email,extra\n"
           '"line one\nline two, with comma",2024-01-01T00:00:00+02:00,S,T-9,x@y.io,ignored\n\n').encode()
    result = ingest(".csv", raw)
    assert result.total_rows == 1
    assert result.tickets[0]["body"] == "line one\nline two, with comma"
    assert set(result.tickets[0]) == {"ticket_id", "customer_email", "subject", "body", "created_at"}


@pytest.mark.parametrize("raw, message", [
    (b"", "empty"),
    (b"  \n\n", "empty"),
    (b"id,email\n1,a@b.co\n", "missing required columns"),
    (b"\xff\xfe\x00bad", "UTF-8"),
])
def test_unusable_files(raw, message):
    with pytest.raises(IngestError, match=message):
        ingest(".csv", raw)


def test_header_only():
    assert ingest(".csv", HEADER.encode()).total_rows == 0


def test_jsonl():
    raw = b"\n".join([
        b'{"ticket_id": "J-1", "customer_email": "a@b.co", "subject": "s", "body": "b", "created_at": "2024-01-01"}',
        b"{not json",
        b"[1, 2]",
        b"",
        b'{"ticket_id": "J-2", "customer_email": "a@b.co", "subject": "s", "body": 5, "created_at": "2024-01-01"}',
    ])
    result = ingest(".jsonl", raw)
    assert [t["ticket_id"] for t in result.tickets] == ["J-1"]
    assert [(e["row"], e["field"]) for e in result.errors] == [(2, None), (3, None), (4, "body")]
