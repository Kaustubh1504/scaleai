import json
import warnings

import pytest

warnings.filterwarnings("ignore", message="Using `httpx`")  # starlette TestClient notice
from fastapi.testclient import TestClient  # noqa: E402

from problem_api import SAMPLE_CSV  # noqa: E402

HEADER = "task_id,annotator_email,label,submitted_at\n"


@pytest.fixture
def client(sol, tmp_path):
    return TestClient(sol.create_app(tmp_path))


def upload(client, content, filename="batch.csv"):
    if isinstance(content, str):
        content = content.encode("utf-8")
    return client.post("/uploads", files={"file": (filename, content, "text/csv")})


def ok(resp):
    assert resp.status_code == 201, f"expected 201, got {resp.status_code}: {resp.text[:300]}"
    return resp.json()


def stored_files(tmp_path):
    d = tmp_path / "uploads"
    return sorted(p.name for p in d.iterdir()) if d.exists() else []


def test_sample_upload_summary(client):
    """The sample file: 201 with total/valid/invalid counts and one error per bad row, in row order"""
    body = ok(upload(client, SAMPLE_CSV))
    assert isinstance(body["upload_id"], str) and body["upload_id"], "upload_id must be a non-empty string"
    assert body["filename"] == "batch.csv"
    assert (body["total_rows"], body["valid_rows"], body["invalid_rows"]) == (6, 2, 4)
    assert body["errors"] == [
        {"row": 3, "field": "annotator_email", "message": "invalid email"},
        {"row": 4, "field": "task_id", "message": "duplicate task_id"},
        {"row": 5, "field": "label", "message": "must be one of: negative, neutral, positive"},
        {"row": 6, "field": "submitted_at", "message": "invalid timestamp"},
    ], "errors must follow the rule table, ordered by row"


def test_get_returns_normalised_rows(client):
    """GET /uploads/{id} returns the summary plus valid rows, normalised (lower-case, stripped, UTC Z)"""
    posted = ok(upload(client, SAMPLE_CSV))
    resp = client.get(f"/uploads/{posted['upload_id']}")
    assert resp.status_code == 200, resp.text[:300]
    body = resp.json()
    assert {k: v for k, v in body.items() if k != "rows"} == posted, "GET must include everything POST returned"
    assert body["rows"] == [
        {"task_id": "t-001", "annotator_email": "ana@example.com", "label": "positive",
         "submitted_at": "2024-05-01T10:00:00Z"},
        {"task_id": "t-002", "annotator_email": "ben@example.com", "label": "neutral",
         "submitted_at": "2024-05-01T10:30:00Z"},
    ], "rows keep only the 4 required keys; +02:00 must be converted to UTC"


def test_first_failing_rule_only(client):
    """Each row reports only its first failing rule, checked in table order"""
    csv_text = HEADER + (
        ",bad-email,nope,never\n"              # task_id required wins over everything else
        "t1,,nope,never\n"                     # email required wins over label/timestamp
        "t2,a@b.co,,never\n"                   # label required
        "t3,a@b.co,POSITIVE,\n"                # timestamp required
        "t4,a@b.co,positive,2024-05-01T10:00:00\n"   # no UTC offset
        "t5,a@b,positive,2024-05-01T10:00:00Z\n"     # no dot in domain
        "t6,a@b.co,positive,2024-05-01\n"            # a date has no offset either
    )
    body = ok(upload(client, csv_text))
    got = [(e["row"], e["field"], e["message"]) for e in body["errors"]]
    assert got == [
        (1, "task_id", "required"),
        (2, "annotator_email", "required"),
        (3, "label", "required"),
        (4, "submitted_at", "required"),
        (5, "submitted_at", "invalid timestamp"),
        (6, "annotator_email", "invalid email"),
        (7, "submitted_at", "invalid timestamp"),
    ]
    assert body["valid_rows"] == 0 and body["total_rows"] == 7


def test_wrong_field_count_and_quoted_commas(client):
    """A row with the wrong number of fields gets field null; quoted commas are not separators"""
    csv_text = HEADER + (
        't1,a@b.co,positive,2024-05-01T10:00:00Z\n'
        't2,a@b.co\n'
        't3,a@b.co,positive,2024-05-01T10:00:00Z,extra\n'
        '"t,4",a@b.co,positive,2024-05-01T10:00:00Z\n'
    )
    body = ok(upload(client, csv_text))
    assert body["errors"] == [
        {"row": 2, "field": None, "message": "expected 4 fields, got 2"},
        {"row": 3, "field": None, "message": "expected 4 fields, got 5"},
    ]
    rows = client.get(f"/uploads/{body['upload_id']}").json()["rows"]
    assert [r["task_id"] for r in rows] == ["t1", "t,4"], "use the csv module: \"t,4\" is one field"


def test_duplicate_only_against_valid_rows(client):
    """duplicate task_id compares against earlier VALID rows only"""
    csv_text = HEADER + (
        "t1,broken,positive,2024-05-01T10:00:00Z\n"   # invalid, so t1 is not taken
        "t1,a@b.co,positive,2024-05-01T10:00:00Z\n"   # valid
        " t1 ,c@d.co,negative,2024-05-01T11:00:00Z\n"  # duplicate after stripping
    )
    body = ok(upload(client, csv_text))
    assert [(e["row"], e["message"]) for e in body["errors"]] == [(1, "invalid email"), (3, "duplicate task_id")]
    assert body["valid_rows"] == 1


def test_bom_header_whitespace_blank_lines(client):
    """A UTF-8 BOM, messy header names, extra columns and blank lines are all handled"""
    csv_text = (
        "﻿ Task_ID , Annotator_Email,notes, LABEL ,submitted_at\n"
        "\n"
        "t1,a@b.co,hi,neutral,2024-05-01T10:00:00Z\n"
        "\n"
        "t2,a@b.co,,bogus,2024-05-01T10:00:00Z\n"
    )
    body = ok(upload(client, csv_text))
    assert body["total_rows"] == 2, "blank lines are not rows"
    assert body["errors"] == [{"row": 2, "field": "label", "message": "must be one of: negative, neutral, positive"}], \
        "row numbers count data rows only (blank lines skipped)"


def test_header_only_is_ok_and_uppercase_extension(client):
    """A header-only file is a 201 with zero rows; a .CSV filename is accepted"""
    body = ok(upload(client, HEADER, filename="EXPORT.CSV"))
    assert (body["total_rows"], body["valid_rows"], body["invalid_rows"], body["errors"]) == (0, 0, 0, [])


def test_file_level_errors(client, tmp_path):
    """415 for a non-.csv name; 400 for non-UTF-8, empty files and missing columns; nothing is stored"""
    resp = upload(client, HEADER, filename="batch.xlsx")
    assert resp.status_code == 415, f"non-.csv filename should be 415, got {resp.status_code}"

    resp = upload(client, HEADER.encode() + "t1,a@b.co,positive,caf\xe9\n".encode("latin-1"))
    assert resp.status_code == 400, f"latin-1 bytes are not UTF-8: expected 400, got {resp.status_code}"

    for empty in (b"", b"\n\n"):
        resp = upload(client, empty)
        assert resp.status_code == 400, f"an empty file {empty!r} has no header: expected 400, got {resp.status_code}"

    resp = upload(client, "task_id,label,notes\nt1,positive,x\n")
    assert resp.status_code == 400, f"missing columns should be 400, got {resp.status_code}"
    detail = str(resp.json().get("detail"))
    for col in ("annotator_email", "submitted_at"):
        assert col in detail, f"detail must name the missing column {col!r}: {detail!r}"

    assert [f for f in stored_files(tmp_path) if f.endswith(".json")] == [], "failed uploads must not be stored"


def test_missing_file_field_is_422(client):
    """A request without a `file` field gets FastAPI's 422"""
    resp = client.post("/uploads", files={"upload": ("batch.csv", HEADER.encode(), "text/csv")})
    assert resp.status_code == 422, f"expected 422, got {resp.status_code}"


def test_stored_on_disk_and_survives_restart(sol, tmp_path):
    """Writes storage_dir/uploads/<id>.json; a new app over the same dir serves it; unknown id is 404"""
    first = TestClient(sol.create_app(tmp_path))
    a = ok(upload(first, SAMPLE_CSV))
    b = ok(upload(first, HEADER))
    assert a["upload_id"] != b["upload_id"], "every upload needs its own id"

    path = tmp_path / "uploads" / f"{a['upload_id']}.json"
    assert path.exists(), f"expected {path} to exist"
    on_disk = json.loads(path.read_text())
    assert len(on_disk["rows"]) == 2 and on_disk["valid_rows"] == 2
    assert not [f for f in stored_files(tmp_path) if f.endswith(".tmp")], "leftover temp files"

    second = TestClient(sol.create_app(tmp_path))
    resp = second.get(f"/uploads/{a['upload_id']}")
    assert resp.status_code == 200, "a fresh app over the same storage_dir must find the upload"
    assert resp.json() == on_disk, "GET returns exactly what was stored"
    assert second.get("/uploads/does-not-exist").status_code == 404
    assert second.get("/uploads/" + "0" * 32).status_code == 404
