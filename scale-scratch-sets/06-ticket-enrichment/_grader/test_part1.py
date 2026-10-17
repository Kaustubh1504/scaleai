"""Part 1: CSV -> JSON with validation, safe paths and atomic output."""

import json
from pathlib import Path

import pytest
from conftest import HERE, enrich, keyed

EXPECTED = json.loads((HERE / "expected_sample.json").read_text())
PART1_CODES = {"malformed_row", "missing_ticket_id", "duplicate_ticket_id"}
LATER_KEYS = {"customer", "urgency", "sla_hours"}


def base(rows):
    return [{k: v for k, v in r.items() if k not in LATER_KEYS} for r in rows]


def out_rows(name="tickets.json"):
    return json.loads(Path("output", name).read_text(encoding="utf-8"))


def test_sample_status_and_count(client):
    r = enrich(client)
    assert r.status_code == 200, r.text
    assert r.json()["rows_written"] == 11


def test_sample_rows_exact(client):
    assert enrich(client).status_code == 200
    rows = out_rows()
    assert isinstance(rows, list)
    assert base(rows) == base(EXPECTED["rows"])


def test_sample_errors(client):
    got = enrich(client).json()["errors"]
    assert keyed(got, PART1_CODES) == [(7, "K002", "duplicate_ticket_id"), (8, None, "missing_ticket_id"),
                                       (11, None, "malformed_row")]


def test_bom_whitespace_and_extra_column(client):
    enrich(client)
    row = out_rows()[0]
    assert set(row) >= {"ticket_id", "customer_id", "subject", "body", "channel"}
    assert "﻿ticket_id" not in row and "ticket_id " not in row and " body " not in row
    assert row["channel"] == "email"


def test_values_stripped(client):
    enrich(client)
    k004 = {r["ticket_id"]: r for r in out_rows()}["K004"]
    assert k004["customer_id"] == "C01"
    assert k004["subject"] == "Feature request: dark mode"
    assert k004["body"] == "Would love a dark theme."


def test_quotes_commas_and_multiline(client):
    enrich(client)
    rows = {r["ticket_id"]: r for r in out_rows()}
    assert rows["K001"]["body"] == 'I reset my password twice and still get "invalid credentials".'
    assert rows["K002"]["subject"] == "Billing question, invoice 4471"
    assert rows["K007"]["body"] == "Exports take\nover an hour now"


def test_duplicate_keeps_first(client):
    enrich(client)
    k002 = [r for r in out_rows() if r["ticket_id"] == "K002"]
    assert len(k002) == 1 and k002[0]["subject"] == "Billing question, invoice 4471"


def test_columns_come_from_headers(client, workdir):
    (workdir / "data" / "t2.csv").write_text(
        "body,priority_hint,subject,customer_id,ticket_id\nSome body,p1,Some subject,C01,X1\n", encoding="utf-8")
    r = enrich(client, tickets="data/t2.csv", output="output/t2.json")
    assert r.status_code == 200, r.text
    row = out_rows("t2.json")[0]
    assert (row["ticket_id"], row["subject"], row["body"], row["priority_hint"]) == (
        "X1", "Some subject", "Some body", "p1")


def test_blank_lines_are_ignored(client, workdir):
    (workdir / "data" / "t3.csv").write_text(
        "ticket_id,customer_id,subject,body\n\nA1,C01,s1,b1\n\n,C01,s2,b2\n", encoding="utf-8")
    r = enrich(client, tickets="data/t3.csv", output="output/t3.json")
    assert r.json()["rows_written"] == 1
    assert keyed(r.json()["errors"], PART1_CODES) == [(2, None, "missing_ticket_id")]


@pytest.mark.parametrize("field,value", [
    ("tickets_path", "../tickets.csv"),
    ("tickets_path", "data/../../etc/passwd.csv"),
    ("tickets_path", "/etc/passwd.csv"),
    ("tickets_path", "data/tickets.txt"),
    ("tickets_path", "output/tickets.csv"),
    ("output_path", "../out.json"),
    ("output_path", "data/out.json"),
    ("output_path", "output/out.csv"),
    ("output_path", "/tmp/out.json"),
])
def test_bad_paths_are_400(client, field, value):
    body = {"tickets_path": "data/tickets.csv", "output_path": "output/x.json"}
    body[field] = value
    r = client.post("/enrich", json=body)
    assert r.status_code == 400, (value, r.status_code, r.text)
    assert not Path("output/x.json").exists()


def test_symlink_escape_is_400(client, workdir, tmp_path_factory):
    outside = tmp_path_factory.mktemp("outside") / "secret.csv"
    outside.write_text("ticket_id,customer_id,subject,body\n")
    (workdir / "data" / "link.csv").symlink_to(outside)
    assert enrich(client, tickets="data/link.csv").status_code == 400


def test_missing_file_is_404(client):
    assert enrich(client, tickets="data/nope.csv").status_code == 404


def test_bad_file_is_422(client, workdir):
    (workdir / "data" / "nohdr.csv").write_text("ticket_id,subject,body\nA,b,c\n")
    assert enrich(client, tickets="data/nohdr.csv").status_code == 422
    (workdir / "data" / "empty.csv").write_text("")
    assert enrich(client, tickets="data/empty.csv").status_code == 422
    (workdir / "data" / "latin1.csv").write_bytes("ticket_id,customer_id,subject,body\nA,C01,caf\xe9,x\n".encode("latin-1"))
    assert enrich(client, tickets="data/latin1.csv").status_code == 422


def test_missing_body_field_is_422(client):
    assert client.post("/enrich", json={"tickets_path": "data/tickets.csv"}).status_code == 422


def test_output_subdir_created_and_overwritten(client, workdir):
    target = workdir / "output" / "a" / "b" / "t.json"
    assert enrich(client, output="output/a/b/t.json").status_code == 200
    target.write_text("old junk")
    assert enrich(client, output="output/a/b/t.json").status_code == 200
    assert len(json.loads(target.read_text())) == 11


def test_no_temp_files_left_behind(client, workdir):
    enrich(client)
    assert [p.name for p in (workdir / "output").iterdir()] == ["tickets.json"]


def test_failed_request_leaves_old_output_untouched(client, workdir):
    target = workdir / "output" / "tickets.json"
    target.write_text("[]")
    (workdir / "data" / "bad.csv").write_text("nope\n")
    assert enrich(client, tickets="data/bad.csv").status_code == 422
    assert target.read_text() == "[]"
