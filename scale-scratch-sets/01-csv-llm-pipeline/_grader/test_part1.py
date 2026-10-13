"""Part 1: CSV -> JSON with validation, joins, paths and atomic output."""

import json
from pathlib import Path

import pytest
from conftest import HERE, convert

EXPECTED = json.loads((HERE / "expected_sample.json").read_text())


def strip_cat(rows):
    return [{k: v for k, v in r.items() if k != "category"} for r in rows]


def keyed(errors, drop=("classification_failed",)):
    return sorted((e["file"], e["row"], e["id"], e["error"]) for e in errors if e["error"] not in drop)


def test_sample_status_and_count(client):
    r = convert(client)
    assert r.status_code == 200, r.text
    assert r.json()["rows_written"] == 12


def test_sample_rows_exact(client):
    assert convert(client).status_code == 200
    rows = json.loads(Path("output/tasks.json").read_text(encoding="utf-8"))
    assert isinstance(rows, list)
    assert strip_cat(rows) == strip_cat(EXPECTED["rows"])


def test_sample_errors(client):
    got = convert(client).json()["errors"]
    assert keyed(got) == keyed(EXPECTED["response"]["errors"])


def test_bom_and_whitespace_in_headers(client):
    convert(client)
    row = json.loads(Path("output/tasks.json").read_text())[0]
    assert "task_id" in row and "﻿task_id" not in row and "user_id" in row
    assert "name" in row["user"] and " name " not in row["user"]


def test_quoted_fields_and_multiline(client):
    convert(client)
    rows = {r["task_id"]: r for r in json.loads(Path("output/tasks.json").read_text())}
    assert rows["T002"]["title"] == "Label street scenes, batch 7"
    assert rows["T003"]["user"]["name"] == 'Katherine "Kat" Johnson'
    assert rows["T013"]["description"] == "Spot-check 100 labels\nacross two annotators"


def test_columns_come_from_headers(client, workdir):
    (workdir / "data" / "t2.csv").write_text(
        "priority,due_date,user_id,description,title,task_id,owner_note\n"
        "3,2024-06-01,U01,Do it,Some title,X1,hello\n", encoding="utf-8")
    (workdir / "data" / "u2.csv").write_text("team,user_id,name,region\nops,U01,Ada,eu\n", encoding="utf-8")
    r = convert(client, tasks="data/t2.csv", users="data/u2.csv", output="output/t2.json")
    assert r.status_code == 200, r.text
    row = json.loads((workdir / "output" / "t2.json").read_text())[0]
    assert row["due_date"] == "2024-06-01" and row["owner_note"] == "hello"
    assert row["priority"] == 3
    assert row["user"] == {"team": "ops", "user_id": "U01", "name": "Ada", "region": "eu"}


def test_missing_task_id_is_skipped(client, workdir):
    (workdir / "data" / "t3.csv").write_text(
        "task_id,title,description,user_id,priority\n ,No id,x,U01,1\nA1,Ok,y,U01,1\n", encoding="utf-8")
    r = convert(client, tasks="data/t3.csv", output="output/t3.json")
    assert r.status_code == 200
    assert r.json()["rows_written"] == 1
    assert ("tasks", 1, None, "missing_task_id") in keyed(r.json()["errors"])


def test_blank_lines_are_ignored(client, workdir):
    (workdir / "data" / "t4.csv").write_text(
        "task_id,title,description,user_id,priority\n\nA1,Ok,y,U01,1\n\nA2,Ok2,z,U01,9\n", encoding="utf-8")
    r = convert(client, tasks="data/t4.csv", output="output/t4.json")
    assert r.json()["rows_written"] == 2
    assert keyed(r.json()["errors"], drop=("classification_failed", "duplicate_user_id")) == [
        ("tasks", 2, "A2", "invalid_priority")]


@pytest.mark.parametrize("field,value", [
    ("tasks_path", "../tasks.csv"),
    ("tasks_path", "data/../../etc/passwd.csv"),
    ("tasks_path", "/etc/passwd.csv"),
    ("tasks_path", "data/tasks.txt"),
    ("tasks_path", "output/tasks.csv"),
    ("users_path", "data/../users.csv"),
    ("output_path", "../out.json"),
    ("output_path", "data/out.json"),
    ("output_path", "output/out.csv"),
    ("output_path", "/tmp/out.json"),
])
def test_bad_paths_are_400(client, field, value):
    body = {"tasks_path": "data/tasks.csv", "users_path": "data/users.csv", "output_path": "output/x.json"}
    body[field] = value
    r = client.post("/convert", json=body)
    assert r.status_code == 400, (value, r.status_code, r.text)
    assert not Path("output/x.json").exists()


def test_symlink_escape_is_400(client, workdir, tmp_path_factory):
    outside = tmp_path_factory.mktemp("outside") / "secret.csv"
    outside.write_text("task_id,title,description,user_id,priority\n")
    (workdir / "data" / "link.csv").symlink_to(outside)
    assert convert(client, tasks="data/link.csv").status_code == 400


def test_missing_file_is_404(client):
    assert convert(client, tasks="data/nope.csv").status_code == 404
    assert convert(client, users="data/nope.csv").status_code == 404


def test_missing_header_is_422(client, workdir):
    (workdir / "data" / "bad.csv").write_text("task_id,title,user_id\nA,b,U01\n")
    assert convert(client, tasks="data/bad.csv").status_code == 422
    (workdir / "data" / "empty.csv").write_text("")
    assert convert(client, tasks="data/empty.csv").status_code == 422
    (workdir / "data" / "nouid.csv").write_text("id,name\nU1,x\n")
    assert convert(client, users="data/nouid.csv").status_code == 422


def test_missing_body_field_is_422(client):
    assert client.post("/convert", json={"tasks_path": "data/tasks.csv"}).status_code == 422


def test_output_subdir_created_and_overwritten(client, workdir):
    target = workdir / "output" / "nested" / "deep" / "t.json"
    assert convert(client, output="output/nested/deep/t.json").status_code == 200
    assert len(json.loads(target.read_text())) == 12
    target.write_text("old junk")
    assert convert(client, output="output/nested/deep/t.json").status_code == 200
    assert len(json.loads(target.read_text())) == 12


def test_no_temp_files_left_behind(client, workdir):
    convert(client)
    leftovers = [p.name for p in (workdir / "output").iterdir() if p.name not in ("tasks.json", ".checkpoint")]
    assert leftovers == []


def test_failed_request_leaves_old_output_untouched(client, workdir):
    target = workdir / "output" / "tasks.json"
    target.write_text("[]")
    (workdir / "data" / "bad.csv").write_text("nope\n")
    assert convert(client, tasks="data/bad.csv").status_code == 422
    assert target.read_text() == "[]"
