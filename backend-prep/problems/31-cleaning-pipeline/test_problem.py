import json
import os
from dataclasses import asdict

import pytest

from problem_api import ANNOTATORS_JSON, SUBMISSIONS_CSV

HEADER = "submission_id,task_id,annotator_id,label,submitted_at,payout\n"
OUTPUTS = {"clean.jsonl", "errors.csv", "summary.json"}

SAMPLE_CLEAN = [
    {"submission_id": "S001", "task_id": "T1", "annotator_id": "A01", "label": "cat", "submitted_at": "2024-03-01T10:00:00Z", "payout_cents": 120},
    {"submission_id": "S002", "task_id": "T1", "annotator_id": "A02", "label": "dog", "submitted_at": "2024-03-01T08:05:00Z", "payout_cents": 120},
    {"submission_id": "S008", "task_id": "T4", "annotator_id": "A01", "label": "cat", "submitted_at": "2024-03-01T09:30:00Z", "payout_cents": 200},
    {"submission_id": "S009", "task_id": "T4", "annotator_id": "A02", "label": "cat", "submitted_at": "2024-03-01T11:00:00Z", "payout_cents": 200},
    {"submission_id": "S011", "task_id": "T5", "annotator_id": "A03", "label": "other", "submitted_at": "2024-03-01T15:00:00Z", "payout_cents": 100000},
    {"submission_id": "S012", "task_id": "T5", "annotator_id": "A02", "label": "dog", "submitted_at": "2024-03-01T16:00:00Z", "payout_cents": 50},
    {"submission_id": "S013", "task_id": "T6", "annotator_id": "A04", "label": "cat", "submitted_at": "2024-03-01T18:00:00Z", "payout_cents": 25},
    {"submission_id": "S014", "task_id": "T6", "annotator_id": "A01", "label": "cat", "submitted_at": "2024-03-01T18:00:00Z", "payout_cents": 25},
]

SAMPLE_ERRORS = """line,field,reason
4,label,bad_label
5,submitted_at,bad_timestamp
6,task_id,missing
7,annotator_id,unknown_annotator
9,payout,bad_payout
11,submission_id,superseded
14,label,missing
14,payout,bad_payout
18,submission_id,superseded
20,submission_id,superseded
22,submitted_at,missing
22,payout,missing
"""

SAMPLE_SUMMARY = {"rows_read": 19, "invalid_rows": 6, "duplicates_dropped": 1, "conflicts": 3,
                  "superseded_rows": 3, "unknown_annotator_rows": 1, "clean_rows": 8}


def write_inputs(tmp_path, csv_text, annotators=("A01", "A02")):
    csv_path = tmp_path / "in.csv"
    csv_path.write_bytes(csv_text.encode("utf-8"))
    ann_path = tmp_path / "annotators.json"
    ann_path.write_text(json.dumps([{"annotator_id": a, "name": a.lower()} for a in annotators]))
    return csv_path, ann_path


def run(sol, tmp_path, csv_text, annotators=("A01", "A02")):
    csv_path, ann_path = write_inputs(tmp_path, csv_text, annotators)
    out = tmp_path / "out"
    summary = sol.run_pipeline(csv_path, ann_path, out)
    return summary, out


def read_clean(out):
    text = (out / "clean.jsonl").read_text()
    return [json.loads(line) for line in text.splitlines()]


def test_sample_clean_jsonl(sol, tmp_path):
    """Sample: clean.jsonl has the 8 expected records, exact bytes, sorted by submission_id"""
    sol.run_pipeline(SUBMISSIONS_CSV, ANNOTATORS_JSON, tmp_path)
    got = read_clean(tmp_path)
    assert [r["submission_id"] for r in got] == [r["submission_id"] for r in SAMPLE_CLEAN], "wrong set or order of ids"
    for g, w in zip(got, SAMPLE_CLEAN):
        assert g == w, f"{w['submission_id']}: got {g}, expected {w}"
    expected = "".join(json.dumps(r) + "\n" for r in SAMPLE_CLEAN)
    assert (tmp_path / "clean.jsonl").read_text() == expected, "use json.dumps(record) per line, keys in spec order, \\n endings"


def test_sample_errors_csv(sol, tmp_path):
    """Sample: errors.csv lists every failing field, superseded version and unknown annotator by line"""
    sol.run_pipeline(SUBMISSIONS_CSV, ANNOTATORS_JSON, tmp_path)
    got = (tmp_path / "errors.csv").read_bytes().decode()
    assert got.splitlines() == SAMPLE_ERRORS.splitlines(), "errors.csv content differs (lines count blank lines too)"
    assert got == SAMPLE_ERRORS, "use \\n line endings and a trailing newline"


def test_sample_summary(sol, tmp_path):
    """Sample: returns the Summary and writes summary.json with the same counts"""
    summary = sol.run_pipeline(SUBMISSIONS_CSV, ANNOTATORS_JSON, tmp_path)
    assert isinstance(summary, sol.Summary)
    assert asdict(summary) == SAMPLE_SUMMARY
    assert (tmp_path / "summary.json").read_text() == json.dumps(SAMPLE_SUMMARY, indent=2) + "\n"


def test_headers_bom_and_short_rows(sol, tmp_path):
    """BOM, messy/reordered headers and extra columns are handled; short rows have empty (missing) cells"""
    text = ("﻿ PAYOUT ,Notes, Label,submitted_at ,ANNOTATOR_ID,task_id,Submission_Id\r\n"
            "$3,hi,DOG,2024-03-01T10:00:00Z,a01,t9,s1\r\n"
            "\r\n"
            " , , , , , , \r\n"
            "$3,hi,cat\r\n")
    summary, out = run(sol, tmp_path, text)
    assert read_clean(out) == [{"submission_id": "S1", "task_id": "T9", "annotator_id": "A01", "label": "dog",
                                "submitted_at": "2024-03-01T10:00:00Z", "payout_cents": 300}]
    assert (out / "errors.csv").read_text() == (
        "line,field,reason\n5,submission_id,missing\n5,task_id,missing\n5,annotator_id,missing\n5,submitted_at,missing\n"
    ), "short row on line 5: errors in column order; blank and all-whitespace rows are skipped but counted as lines"
    assert summary.rows_read == 2 and summary.invalid_rows == 1


def test_normalization_rules(sol, tmp_path):
    """Timestamps (offset, naive, space, epoch, fraction) and payouts normalize exactly; bad values are rejected"""
    text = HEADER + (
        "a,t,A01,cat,2024-03-01T01:30:00-05:00,0.5\n"
        "b,t,A01,Cat,2024-03-01 06:30:00,\"$1,234.05\"\n"
        "c,t,A01,cat,1709290800,7\n"
        "d,t,A01,cat,2024-03-01T06:30:00.999Z,$0.07\n"
        "e,t,A01,cat,03/01/2024,$1\n"
        "f,t,A01,cat,2024-03-01T06:30:00Z,1.234\n"
        "g,t,A01,cat,2024-03-01T06:30:00Z,-5\n"
        "h,t,A01,cat,2024-03-01T06:30:00Z,1e3\n"
    )
    summary, out = run(sol, tmp_path, text)
    got = {r["submission_id"]: (r["submitted_at"], r["payout_cents"]) for r in read_clean(out)}
    assert got == {
        "A": ("2024-03-01T06:30:00Z", 50), "B": ("2024-03-01T06:30:00Z", 123405),
        "C": ("2024-03-01T11:00:00Z", 700), "D": ("2024-03-01T06:30:00Z", 7),
    }
    assert (out / "errors.csv").read_text().splitlines()[1:] == [
        "6,submitted_at,bad_timestamp", "7,payout,bad_payout", "8,payout,bad_payout", "9,payout,bad_payout",
    ]
    assert summary.invalid_rows == 4


def test_exact_duplicates_dropped_silently(sol, tmp_path):
    """Rows identical after normalization are dropped silently and counted in duplicates_dropped"""
    text = HEADER + (
        "S1,T1,A01,cat,2024-03-01T10:00:00Z,$1.00\n"
        " s1 ,t1,a01,CAT,2024-03-01T11:00:00+01:00,1\n"
        "S1,T1,A01,cat,2024-03-01T10:00:00Z,1.00\n"
    )
    summary, out = run(sol, tmp_path, text)
    assert len(read_clean(out)) == 1
    assert (out / "errors.csv").read_text() == "line,field,reason\n", "exact duplicates are not errors"
    assert (summary.duplicates_dropped, summary.conflicts, summary.clean_rows) == (2, 0, 1)


def test_conflicts_latest_wins(sol, tmp_path):
    """Conflicting versions: latest instant wins, ties go to the later line, losers are 'superseded'"""
    text = HEADER + (
        "S1,T1,A01,dog,2024-03-01T16:00:00Z,$1\n"         # line 2: 16:00Z wins
        "S1,T1,A01,cat,2024-03-01T17:00:00+02:00,$1\n"    # line 3: 15:00Z (string looks later)
        "S2,T1,A01,dog,2024-03-01T10:00:00Z,$1\n"         # line 4: tie, earlier line -> superseded
        "S2,T1,A01,cat,2024-03-01T10:00:00Z,$1\n"         # line 5: tie, later line wins
        "S1,T1,A01,cat,2024-03-01T17:00:00+02:00,$1\n"    # line 6: exact copy of line 3
    )
    summary, out = run(sol, tmp_path, text)
    assert [(r["submission_id"], r["label"]) for r in read_clean(out)] == [("S1", "dog"), ("S2", "cat")]
    assert (out / "errors.csv").read_text() == "line,field,reason\n3,submission_id,superseded\n4,submission_id,superseded\n"
    assert (summary.conflicts, summary.superseded_rows, summary.duplicates_dropped) == (2, 2, 1), \
        "an exact copy of a losing version is a duplicate, not a second superseded row"


def test_unknown_annotator_after_dedupe(sol, tmp_path):
    """References are checked after dedupe: a winning version with an unknown annotator yields no clean row"""
    text = HEADER + (
        "S1,T1,A01,cat,2024-03-01T10:00:00Z,$1\n"
        "S1,T1,A77,cat,2024-03-01T11:00:00Z,$1\n"
        "S2,T1,a02 ,dog,2024-03-01T10:00:00Z,$1\n"
    )
    summary, out = run(sol, tmp_path, text, annotators=(" a01", "A02 "))
    assert [r["submission_id"] for r in read_clean(out)] == ["S2"], "annotator ids from JSON are normalized too"
    assert (out / "errors.csv").read_text() == (
        "line,field,reason\n2,submission_id,superseded\n3,annotator_id,unknown_annotator\n")
    assert asdict(summary) == {"rows_read": 3, "invalid_rows": 0, "duplicates_dropped": 0, "conflicts": 1,
                               "superseded_rows": 1, "unknown_annotator_rows": 1, "clean_rows": 1}


def test_idempotent_and_no_stray_files(sol, tmp_path):
    """Creates out_dir, writes exactly the three outputs, and a re-run produces byte-identical files"""
    out = tmp_path / "nested" / "out"
    sol.run_pipeline(SUBMISSIONS_CSV, ANNOTATORS_JSON, out)
    first = {p.name: p.read_bytes() for p in out.iterdir()}
    assert set(first) == OUTPUTS, f"out_dir must contain exactly {sorted(OUTPUTS)}, found {sorted(first)}"
    sol.run_pipeline(SUBMISSIONS_CSV, ANNOTATORS_JSON, out)
    second = {p.name: p.read_bytes() for p in out.iterdir()}
    assert second == first, "re-running on the same input must produce byte-identical outputs"


def test_missing_column_writes_nothing(sol, tmp_path):
    """A missing required column raises ValueError and leaves previous outputs untouched"""
    out = tmp_path / "out"
    out.mkdir()
    for name in OUTPUTS:
        (out / name).write_text(f"old {name}\n")
    csv_path, ann_path = write_inputs(tmp_path, "submission_id,task_id,annotator_id,label,submitted_at\nS1,T1,A01,cat,x\n")
    with pytest.raises(ValueError):
        sol.run_pipeline(csv_path, ann_path, out)
    assert {p.name: p.read_text() for p in out.iterdir()} == {n: f"old {n}\n" for n in OUTPUTS}


def test_atomic_when_replace_fails(sol, tmp_path, monkeypatch):
    """If os.replace fails, the error propagates, old outputs are intact and no temp files remain"""
    out = tmp_path / "out"
    out.mkdir()
    for name in OUTPUTS:
        (out / name).write_text(f"old {name}\n")

    calls = []

    def broken_replace(src, dst, *a, **kw):
        calls.append((str(src), str(dst)))
        raise OSError("disk full (simulated)")

    monkeypatch.setattr(os, "replace", broken_replace)
    with pytest.raises(OSError):
        sol.run_pipeline(SUBMISSIONS_CSV, ANNOTATORS_JSON, out)
    monkeypatch.undo()

    assert calls, "move outputs into place with os.replace (or Path.replace)"
    src_dirs = {os.path.dirname(os.path.abspath(src)) for src, _ in calls}
    assert src_dirs == {str(out.resolve())} or src_dirs == {str(out)}, \
        "temp files must live in out_dir so the rename is atomic (same filesystem)"
    leftovers = sorted(p.name for p in out.iterdir() if p.name not in OUTPUTS)
    assert not leftovers, f"temp files left behind: {leftovers}"
    assert {p.name: p.read_text() for p in out.iterdir()} == {n: f"old {n}\n" for n in OUTPUTS}, \
        "previous outputs must be untouched when the run fails"
