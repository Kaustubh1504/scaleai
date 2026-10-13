"""Part 1: multipart upload, upload checks, CSV parsing, validation and join."""

import json
import tempfile

import pytest
from conftest import HERE, MIB, upload

EXPECTED = json.loads((HERE / "expected_sample.json").read_text())
TASK_HEADER = "task_id,title,description,user_id,priority\n"


def strip_cat(rows):
    return [{k: v for k, v in r.items() if k != "category"} for r in rows]


def keyed(errors, drop=("classification_failed",)):
    return sorted((e["file"], e["row"], e["id"], e["error"]) for e in errors if e["error"] not in drop)


def csv_of_size(header, row, size):
    """Valid CSV of exactly `size` bytes: header, then row(i, pad) lines; the last row is padded."""
    out = header
    i = 0
    while len(out) + 2 * len(row(i, "")) < size:
        out += row(i, "")
        i += 1
    out += row(i, "x" * (size - len(out) - len(row(i, ""))))
    data = out.encode()
    assert len(data) == size
    return data


def big_tasks(size):
    return csv_of_size(TASK_HEADER, lambda i, pad: f"B{i:06d},Bulk task {i},Some description{pad},U01,2\n", size)


def big_users(size):
    return csv_of_size("user_id,name\n", lambda i, pad: f"V{i:06d},Name {i}{pad}\n", size)


# ---------------------------------------------------------------- sample


def test_sample_rows_exact(client):
    r = upload(client)
    assert r.status_code == 200, r.text
    rows = r.json()["rows"]
    assert isinstance(rows, list)
    assert rows == strip_cat(EXPECTED["rows"])


def test_sample_errors(client):
    got = upload(client).json()["errors"]
    assert keyed(got) == keyed(EXPECTED["errors"])


def test_no_category_and_no_file_written(client, workdir, llm):
    r = upload(client)
    assert r.status_code == 200
    assert all("category" not in row for row in r.json()["rows"])
    assert llm.count(None) == 0
    assert list(workdir.iterdir()) == [], "Part 1 must not write any file"


def test_bom_and_whitespace_in_headers(client):
    row = upload(client).json()["rows"][0]
    assert "task_id" in row and "﻿task_id" not in row and "user_id" in row
    assert "name" in row["user"] and " name " not in row["user"]


def test_quoted_fields_and_multiline(client):
    rows = {r["task_id"]: r for r in upload(client).json()["rows"]}
    assert rows["T002"]["title"] == "Label street scenes, batch 7"
    assert rows["T003"]["user"]["name"] == 'Katherine "Kat" Johnson'
    assert rows["T013"]["description"] == "Spot-check 100 labels\nacross two annotators"


def test_columns_come_from_headers(client):
    tasks = (b"priority,due_date,user_id,description,title,task_id,owner_note\n"
             b"3,2024-06-01,U01,Do it,Some title,X1,hello\n")
    users = b"team,user_id,name,region\nops,U01,Ada,eu\n"
    r = upload(client, tasks=tasks, users=users)
    assert r.status_code == 200, r.text
    row = r.json()["rows"][0]
    assert row["due_date"] == "2024-06-01" and row["owner_note"] == "hello"
    assert row["priority"] == 3
    assert row["user"] == {"team": "ops", "user_id": "U01", "name": "Ada", "region": "eu"}


def test_missing_task_id_is_skipped(client):
    r = upload(client, tasks=(TASK_HEADER + " ,No id,x,U01,1\nA1,Ok,y,U01,1\n").encode())
    assert r.status_code == 200
    assert [x["task_id"] for x in r.json()["rows"]] == ["A1"]
    assert ("tasks", 1, None, "missing_task_id") in keyed(r.json()["errors"])


def test_blank_lines_are_ignored(client):
    r = upload(client, tasks=(TASK_HEADER + "\nA1,Ok,y,U01,1\n\nA2,Ok2,z,U01,9\n").encode())
    assert len(r.json()["rows"]) == 2
    assert keyed(r.json()["errors"], drop=("classification_failed", "duplicate_user_id")) == [
        ("tasks", 2, "A2", "invalid_priority")]


def test_header_only_file_is_ok(client):
    r = upload(client, tasks=TASK_HEADER.encode())
    assert r.status_code == 200, r.text
    assert r.json()["rows"] == []


# ---------------------------------------------------------------- 415


@pytest.mark.parametrize("field,name", [
    ("tasks", "tasks.txt"),
    ("tasks", "tasks.csv.txt"),
    ("tasks", "csv"),
    ("users", "users.json"),
])
def test_wrong_extension_is_415(client, field, name):
    r = upload(client, **{f"{field}_name": name})
    assert r.status_code == 415, (name, r.status_code, r.text)


def test_extension_is_case_insensitive(client):
    r = upload(client, tasks_name="TASKS.CSV", users_name="Users.Csv")
    assert r.status_code == 200, r.text


# ---------------------------------------------------------------- 413


def test_exactly_one_mib_is_ok(client):
    tasks, users = big_tasks(MIB), big_users(MIB)
    r = upload(client, tasks=tasks, users=users)
    assert r.status_code == 200, r.text
    rows = r.json()["rows"]
    assert len(rows) == tasks.count(b"\n") - 1
    assert rows[-1]["description"].endswith("x") and rows[-1]["priority"] == 2


@pytest.mark.parametrize("field", ["tasks", "users"])
def test_one_byte_over_is_413(client, field):
    files = {"tasks": big_tasks(MIB) if field == "tasks" else None,
             "users": big_users(MIB) if field == "users" else None}
    files[field] += b"\n"  # a trailing blank line: still valid CSV, just one byte too many
    r = upload(client, **files)
    assert r.status_code == 413, r.text


def test_reads_in_chunks_and_stops_early(client, monkeypatch):
    """A 20 MiB upload is rejected having read at most about 1 MiB of it from the upload."""
    import starlette.formparsers as fp

    counter = {"bytes": 0, "files": 0}

    class Counting(tempfile.SpooledTemporaryFile):
        def __init__(self, *a, **kw):
            counter["files"] += 1
            super().__init__(*a, **kw)

        def _count(self, data):
            counter["bytes"] += len(data) if isinstance(data, (bytes, bytearray)) else (data or 0)
            return data

        def read(self, *a):
            return self._count(super().read(*a))

        def read1(self, *a):
            return self._count(super().read1(*a))

        def readline(self, *a):
            return self._count(super().readline(*a))

        def readlines(self, *a):
            lines = super().readlines(*a)
            counter["bytes"] += sum(map(len, lines))
            return lines

        def readinto(self, b):
            return self._count(super().readinto(b))

        def readinto1(self, b):
            return self._count(super().readinto1(b))

        def __iter__(self):
            while line := self.readline():
                yield line

    monkeypatch.setattr(fp, "SpooledTemporaryFile", Counting)
    huge = TASK_HEADER.encode() + b"Z1,Huge,desc,U01,1\n" * (20 * MIB // 19)
    r = upload(client, tasks=huge)
    assert r.status_code == 413, r.text
    assert counter["files"] >= 1, "grader hook not installed (starlette changed?)"
    assert counter["bytes"] <= 2 * MIB, (
        f"read {counter['bytes']} bytes of a {len(huge)}-byte upload; read in chunks and stop once past 1 MiB")


# ---------------------------------------------------------------- 422


@pytest.mark.parametrize("field", ["tasks", "users"])
def test_not_utf8_is_422(client, field):
    bad = {"tasks": (TASK_HEADER + "A1,Caf\xe9 task,d,U01,1\n").encode("latin-1"),
           "users": "user_id,name\nU01,Jos\xe9\n".encode("latin-1")}[field]
    assert upload(client, **{field: bad}).status_code == 422


@pytest.mark.parametrize("field,content", [
    ("tasks", b"task_id,title,user_id\nA,b,U01\n"),
    ("tasks", b""),
    ("tasks", b"\xef\xbb\xbf"),        # BOM only: still empty
    ("users", b"id,name\nU1,x\n"),
    ("users", b""),
])
def test_missing_header_or_empty_is_422(client, field, content):
    assert upload(client, **{field: content}).status_code == 422


@pytest.mark.parametrize("omit", [("users",), ("tasks",), ("tasks", "users")])
def test_missing_form_field_is_422(client, omit):
    assert upload(client, omit=omit).status_code == 422


# ---------------------------------------------------------------- order of checks


def test_extension_checked_before_size(client):
    assert upload(client, tasks=big_tasks(MIB) + b"\n", tasks_name="tasks.txt").status_code == 415
    # both names are checked before either file is read
    assert upload(client, tasks=big_tasks(MIB) + b"\n", users_name="users.txt").status_code == 415


def test_size_checked_before_encoding(client):
    bad = big_tasks(MIB)[:-2] + b"\xe9\n\n"
    assert upload(client, tasks=bad).status_code == 413
