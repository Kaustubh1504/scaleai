"""Part 1: upload, validation, storage."""

import json

import pytest

from conftest import upload

HEADER = "ticket_id,customer_email,subject,body,created_at\n"
EXPECTED_ERRORS = [(6, "customer_email"), (7, "subject"), (9, "ticket_id"), (10, "created_at"), (11, None),
                   (12, None), (13, "ticket_id"), (16, "created_at"), (18, "body")]
VALID_IDS = ["T-1001", "T-1002", "T-1003", "T-1004", "T-1005", "T-1008", "T-1012", "T-1013", "T-1015"]


def test_sample_counts_and_errors(make_client):
    resp = upload(make_client())
    assert resp.status_code == 201
    body = resp.json()
    assert body["filename"] == "tickets.csv"
    assert (body["total_rows"], body["valid_rows"], body["invalid_rows"]) == (18, 9, 9)
    assert [(e["row"], e["field"]) for e in body["errors"]] == EXPECTED_ERRORS
    assert all(isinstance(e["message"], str) and e["message"] for e in body["errors"])
    assert isinstance(body["upload_id"], str) and body["upload_id"]


def test_saved_file_and_get(make_client, tmp_path):
    client = make_client()
    body = upload(client).json()
    path = tmp_path / "uploads" / f"{body['upload_id']}.json"
    assert path.exists()
    saved = json.loads(path.read_text())
    assert [t["ticket_id"] for t in saved["tickets"]] == VALID_IDS
    got = client.get(f"/uploads/{body['upload_id']}")
    assert got.status_code == 200
    assert got.json()["tickets"] == saved["tickets"]
    for key in ("upload_id", "filename", "total_rows", "valid_rows", "invalid_rows", "errors"):
        assert got.json()[key] == body[key]


def test_ticket_fields_are_stripped_strings(make_client):
    client = make_client()
    upload_id = upload(client).json()["upload_id"]
    tickets = {t["ticket_id"]: t for t in client.get(f"/uploads/{upload_id}").json()["tickets"]}
    assert tickets["T-1005"] == {"ticket_id": "T-1005", "customer_email": "eli@example.com", "subject": "Hello",
                                 "body": "Just saying thanks for the great support team!",
                                 "created_at": "2024-05-02T09:30:00Z"}
    assert tickets["T-1008"]["body"] == "Why does my invoice show two charges, one for $10 and one for $12?"
    assert tickets["T-1012"]["body"] == "First line of the body.\nSecond line asks about a refund for a payment."
    assert tickets["T-1015"]["subject"] == "Café ☕"


def test_unknown_upload_is_404(make_client):
    assert make_client().get("/uploads/does-not-exist").status_code == 404


def test_reordered_and_extra_columns(make_client):
    body = upload(make_client(), "tickets_reordered.csv").json()
    assert (body["valid_rows"], body["invalid_rows"]) == (1, 0)


@pytest.mark.parametrize("name, content", [
    ("tickets.csv", b""),
    ("tickets.csv", b"\n\n"),
    ("tickets_bad_header.csv", None),
    ("tickets.csv", "ticket_id,subject,body,created_at\nT-1,s,b,2024-01-01T00:00:00Z\n".encode()),
    ("tickets.csv", HEADER.encode() + b"T-1,a@b.co,\xff\xfe,b,2024-01-01T00:00:00Z\n"),
])
def test_unusable_files_are_400(make_client, name, content):
    assert upload(make_client(), name, content).status_code == 400


@pytest.mark.parametrize("name", ["tickets.txt", "tickets.xlsx", "tickets"])
def test_unsupported_extension_is_415(make_client, name):
    assert upload(make_client(), name, HEADER.encode()).status_code == 415


def test_uppercase_extension_accepted(make_client):
    assert upload(make_client(), "TICKETS.CSV", HEADER.encode()).status_code == 201


def test_missing_file_field_is_422(make_client):
    assert make_client().post("/uploads").status_code == 422


def test_header_only_and_bom(make_client):
    body = upload(make_client(), "tickets.csv", ("﻿" + HEADER).encode()).json()
    assert (body["total_rows"], body["valid_rows"], body["invalid_rows"], body["errors"]) == (0, 0, 0, [])


def test_duplicate_of_invalid_row_is_allowed(make_client):
    content = (HEADER + "T-1,bad,s,b,2024-01-01T00:00:00Z\nT-1,a@b.co,s,b,2024-01-01T00:00:00Z\n"
               "T-1,c@d.co,s,b,2024-01-01T00:00:00Z\n").encode()
    body = upload(make_client(), "t.csv", content).json()
    assert [(e["row"], e["field"]) for e in body["errors"]] == [(1, "customer_email"), (3, "ticket_id")]


def test_rule_order(make_client):
    content = (HEADER + ",bad,,,nope\nT-2,a@b.co,,,nope\nT-3,a@b.co,s,,nope\n").encode()
    body = upload(make_client(), "t.csv", content).json()
    assert [e["field"] for e in body["errors"]] == ["ticket_id", "subject", "body"]


@pytest.mark.change
def test_jsonl_upload(make_client):
    client = make_client()
    resp = upload(client, "tickets.jsonl")
    assert resp.status_code == 201
    body = resp.json()
    assert (body["total_rows"], body["valid_rows"], body["invalid_rows"]) == (7, 2, 5)
    assert [(e["row"], e["field"]) for e in body["errors"]] == [
        (3, None), (4, None), (5, "body"), (6, "body"), (7, "ticket_id")]
    tickets = client.get(f"/uploads/{body['upload_id']}").json()["tickets"]
    assert [t["ticket_id"] for t in tickets] == ["J-1", "J-2"]
    assert set(tickets[1]) == {"ticket_id", "customer_email", "subject", "body", "created_at"}
