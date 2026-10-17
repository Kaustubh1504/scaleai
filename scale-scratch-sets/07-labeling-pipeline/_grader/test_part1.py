"""Part 1: two CSVs -> per-task consensus, validation, safe paths, atomic output."""

import json
from pathlib import Path

import pytest
from conftest import HERE, keyed, run

EXPECTED = json.loads((HERE / "expected_sample.json").read_text())
PART1_CODES = {"malformed_row", "missing_task_id", "duplicate_task_id", "missing_annotator_id", "unknown_task",
               "invalid_label", "duplicate_annotation"}
LATER_KEYS = {"final_label", "resolved_by", "callback"}


def base(rows):
    return [{k: v for k, v in r.items() if k not in LATER_KEYS} for r in rows]


def out(name="labels.json"):
    return json.loads(Path("output", name).read_text(encoding="utf-8"))


def by_id(name="labels.json"):
    return {r["task_id"]: r for r in out(name)}


def test_sample_status_and_count(client):
    r = run(client)
    assert r.status_code == 200, r.text
    assert r.json()["tasks_written"] == 10


def test_sample_rows_exact(client):
    assert run(client).status_code == 200
    rows = out()
    assert isinstance(rows, list)
    assert base(rows) == base(EXPECTED["rows"])


def test_sample_errors(client):
    got = run(client).json()["errors"]
    assert keyed(got, PART1_CODES) == keyed(EXPECTED["response"]["errors"], PART1_CODES)


def test_task_order_is_input_order(client):
    run(client)
    assert [r["task_id"] for r in out()] == [f"P{i:02d}" for i in range(1, 11)]


def test_headers_and_values_clean(client):
    run(client)
    rows = by_id()
    assert set(rows["P01"]) >= {"task_id", "text", "project"}
    assert "﻿task_id" not in rows["P01"] and " text " not in rows["P01"]
    assert rows["P06"]["text"] == "Lovely photo of the beach" and rows["P06"]["project"] == "mod-v2"
    assert rows["P02"]["votes"] == {"safe": 3, "spam": 1}  # " safe " counted as safe


def test_quotes_commas_multiline(client):
    run(client)
    rows = by_id()
    assert rows["P04"]["text"] == "Nobody likes you, just leave"
    assert rows["P05"]["text"] == 'Limited offer: free crypto "giveaway"'
    assert rows["P07"]["text"] == "You people are the worst,\ngo away"


@pytest.mark.parametrize("tid,status,label,agreement,n", [
    ("P01", "agreed", "spam", 1.0, 3),
    ("P02", "agreed", "safe", 0.75, 4),
    ("P03", "agreed", "violence", 0.67, 3),     # exactly 2/3 counts as agreed
    ("P04", "disputed", None, 0.5, 4),
    ("P05", "insufficient", None, 1.0, 2),      # duplicate + invalid label leave only 2 votes
    ("P07", "disputed", None, 0.33, 3),
    ("P10", "insufficient", None, None, 0),     # no annotations at all
])
def test_consensus_rules(client, tid, status, label, agreement, n):
    run(client)
    row = by_id()[tid]
    assert (row["status"], row["consensus_label"], row["agreement"], row["num_annotations"]) == (
        status, label, agreement, n)


def test_two_thirds_boundary(client, workdir):
    (workdir / "data" / "t.csv").write_text("task_id,text\nX1,a\nX2,b\n", encoding="utf-8")
    ann = ["task_id,annotator_id,label"]
    ann += [f"X1,A{i},{'spam' if i <= 4 else 'safe'}" for i in range(1, 7)]  # 4/6 = 2/3 -> agreed
    ann += [f"X2,A{i},{'spam' if i <= 3 else 'safe'}" for i in range(1, 6)]  # 3/5 < 2/3 -> disputed
    (workdir / "data" / "a.csv").write_text("\n".join(ann) + "\n", encoding="utf-8")
    r = run(client, tasks="data/t.csv", annotations="data/a.csv", output="output/b.json")
    assert r.status_code == 200, r.text
    rows = by_id("b.json")
    assert (rows["X1"]["status"], rows["X1"]["consensus_label"]) == ("agreed", "spam")
    assert rows["X2"]["status"] == "disputed"


def test_columns_come_from_headers(client, workdir):
    (workdir / "data" / "t.csv").write_text("lang,text,task_id\nen,hello,Z1\n", encoding="utf-8")
    (workdir / "data" / "a.csv").write_text(
        "label,task_id,annotator_id,confidence\nsafe,Z1,A1,0.9\nsafe,Z1,A2,0.8\nsafe,Z1,A3,1\n", encoding="utf-8")
    r = run(client, tasks="data/t.csv", annotations="data/a.csv", output="output/c.json")
    assert r.status_code == 200, r.text
    row = out("c.json")[0]
    assert (row["task_id"], row["text"], row["lang"], row["status"], row["consensus_label"]) == (
        "Z1", "hello", "en", "agreed", "safe")


@pytest.mark.parametrize("field,value", [
    ("tasks_path", "../tasks.csv"),
    ("tasks_path", "data/../../etc/passwd.csv"),
    ("tasks_path", "/etc/passwd.csv"),
    ("tasks_path", "data/tasks.txt"),
    ("annotations_path", "data/../annotations.csv"),
    ("annotations_path", "output/annotations.csv"),
    ("output_path", "../out.json"),
    ("output_path", "data/out.json"),
    ("output_path", "output/out.csv"),
    ("output_path", "/tmp/out.json"),
])
def test_bad_paths_are_400(client, field, value):
    body = {"tasks_path": "data/tasks.csv", "annotations_path": "data/annotations.csv", "output_path": "output/x.json"}
    body[field] = value
    r = client.post("/consensus", json=body)
    assert r.status_code == 400, (value, r.status_code, r.text)
    assert not Path("output/x.json").exists()


def test_symlink_escape_is_400(client, workdir, tmp_path_factory):
    outside = tmp_path_factory.mktemp("outside") / "secret.csv"
    outside.write_text("task_id,text\n")
    (workdir / "data" / "link.csv").symlink_to(outside)
    assert run(client, tasks="data/link.csv").status_code == 400


def test_missing_file_is_404(client):
    assert run(client, tasks="data/nope.csv").status_code == 404
    assert run(client, annotations="data/nope.csv").status_code == 404


def test_bad_file_is_422(client, workdir):
    (workdir / "data" / "nolabel.csv").write_text("task_id,annotator_id\nP01,A1\n")
    assert run(client, annotations="data/nolabel.csv").status_code == 422
    (workdir / "data" / "empty.csv").write_text("")
    assert run(client, tasks="data/empty.csv").status_code == 422
    (workdir / "data" / "latin1.csv").write_bytes("task_id,text\nP01,caf\xe9\n".encode("latin-1"))
    assert run(client, tasks="data/latin1.csv").status_code == 422


def test_missing_body_field_is_422(client):
    assert client.post("/consensus", json={"tasks_path": "data/tasks.csv"}).status_code == 422


def test_output_subdir_created_and_overwritten(client, workdir):
    target = workdir / "output" / "a" / "b" / "l.json"
    assert run(client, output="output/a/b/l.json").status_code == 200
    target.write_text("old junk")
    assert run(client, output="output/a/b/l.json").status_code == 200
    assert len(json.loads(target.read_text())) == 10


def test_no_temp_files_left_behind(client, workdir):
    run(client)
    assert [p.name for p in (workdir / "output").iterdir()] == ["labels.json"]


def test_failed_request_leaves_old_output_untouched(client, workdir):
    target = workdir / "output" / "labels.json"
    target.write_text("[]")
    (workdir / "data" / "bad.csv").write_text("nope\n")
    assert run(client, tasks="data/bad.csv").status_code == 422
    assert target.read_text() == "[]"
