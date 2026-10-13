import pytest

from conftest import convert, read_output


def error_set(body):
    return {(e["file"], e["row"], e["id"], e["error"]) for e in body["errors"]}


# ---------------------------------------------------------------- Part 1

def test_sample_file(client, workdir):
    r = convert(client)
    assert r.status_code == 200
    body = r.json()
    assert body["rows_written"] == 12
    errors = error_set(body)
    assert ("users", 5, "U02", "duplicate_user_id") in errors
    assert ("tasks", 8, None, "malformed_row") in errors
    assert ("tasks", 9, "T002", "duplicate_task_id") in errors
    assert ("tasks", 5, "T005", "unknown_user") in errors
    assert ("tasks", 6, "T006", "missing_user_id") in errors
    assert ("tasks", 7, "T007", "invalid_priority") in errors

    rows = read_output(workdir)
    first = dict(rows[0])
    first.pop("category")
    assert first == {
        "task_id": "T001", "title": "Transcribe support call 1042",
        "description": "Transcribe the attached 4 minute audio clip.", "user_id": "U01", "priority": 1,
        "user": {"user_id": "U01", "name": "Ada Lovelace", "email": "ada@example.com", "team": "labeling"},
    }
    by_id = {row["task_id"]: row for row in rows}
    assert by_id["T004"]["title"] == "Review flagged comments"
    assert by_id["T005"]["user"] is None


def test_bom_and_whitespace_headers(client, workdir):
    (workdir / "data/t.csv").write_text("﻿ task_id ,title , description,user_id, priority \nA,x,y,U01,1\n",
                                        encoding="utf-8")
    assert convert(client, tasks="data/t.csv").status_code == 200
    row = read_output(workdir)[0]
    assert set(row) == {"task_id", "title", "description", "user_id", "priority", "user", "category"}


def test_quoted_comma_escaped_quote_multiline(client, workdir):
    (workdir / "data/t.csv").write_text(
        'task_id,title,description,user_id,priority\n'
        'A,"a, b","say ""hi""",U01,1\n'
        'B,"line1\nline2",d,U01,2\n'
        '\n'
        'C,c,d,U01,9\n'
    )
    body = convert(client, tasks="data/t.csv").json()
    rows = read_output(workdir)
    assert [r["title"] for r in rows] == ["a, b", "line1\nline2", "c"]
    assert rows[0]["description"] == 'say "hi"'
    # multiline record is row 2 and the blank line doesn't count, so C is row 3
    assert ("tasks", 3, "C", "invalid_priority") in error_set(body)


@pytest.mark.parametrize("field,value", [
    ("tasks_path", "../data/tasks.csv"),
    ("tasks_path", "data/../../etc/passwd.csv"),
    ("tasks_path", "/etc/passwd.csv"),
    ("tasks_path", "output/tasks.csv"),       # wrong root
    ("tasks_path", "data/tasks.txt"),         # wrong extension
    ("output_path", "data/out.json"),         # wrong root
    ("output_path", "output/../x.json"),
    ("output_path", "output/out.csv"),
])
def test_bad_paths_400(client, field, value):
    paths = {"tasks": "data/tasks.csv", "users": "data/users.csv", "output": "output/tasks.json"}
    paths[field.removesuffix("_path")] = value
    assert convert(client, **paths).status_code == 400


def test_missing_file_404_and_header_422(client, workdir):
    assert convert(client, tasks="data/nope.csv").status_code == 404
    (workdir / "data/bad.csv").write_text("task_id,title,user_id,priority\nA,x,U01,1\n")
    assert convert(client, tasks="data/bad.csv").status_code == 422
    (workdir / "data/empty.csv").write_text("")
    assert convert(client, tasks="data/empty.csv").status_code == 422
    (workdir / "data/latin1.csv").write_bytes("task_id,title,description,user_id,priority\nA,caf\xe9,d,U01,1\n".encode("latin-1"))
    assert convert(client, tasks="data/latin1.csv").status_code == 422


def test_failed_request_keeps_old_output(client, workdir):
    (workdir / "output/tasks.json").write_text("OLD")
    assert convert(client, tasks="data/nope.csv").status_code == 404
    assert (workdir / "output/tasks.json").read_text() == "OLD"


def test_output_subdir_created_no_temp_files(client, workdir):
    assert convert(client, output="output/a/b/out.json").status_code == 200
    assert [p.name for p in (workdir / "output/a/b").iterdir()] == ["out.json"]


def test_duplicate_keeps_first_and_null_users(client, workdir):
    (workdir / "data/t.csv").write_text(
        "task_id,title,description,user_id,priority\n"
        "A,first,d,U01,1\n"
        "A,second,d,U01,1\n"
        "B,b,d,,1\n"
        "C,c,d,U77,1\n"
    )
    body = convert(client, tasks="data/t.csv").json()
    rows = read_output(workdir)
    assert [r["title"] for r in rows] == ["first", "b", "c"]
    assert rows[1]["user"] is None and rows[2]["user"] is None
    errors = error_set(body)
    assert ("tasks", 2, "A", "duplicate_task_id") in errors
    assert ("tasks", 3, "B", "missing_user_id") in errors
    assert ("tasks", 4, "C", "unknown_user") in errors


# ---------------------------------------------------------------- Part 2

def one_task_csv(workdir, title="Job"):
    (workdir / "data/one.csv").write_text(f"task_id,title,description,user_id,priority\nA,{title},d,U01,1\n")
    return "data/one.csv"


def test_429_then_ok(client, workdir, llm):
    llm.script["Job"] = [429, '{"category": "transcription"}']
    convert(client, tasks=one_task_csv(workdir))
    assert read_output(workdir)[0]["category"] == "transcription"
    assert llm.calls["Job"] == 2


def test_5xx_forever_gives_up_after_4_calls(client, workdir, llm):
    llm.script["Job"] = [500]
    body = convert(client, tasks=one_task_csv(workdir)).json()
    assert read_output(workdir)[0]["category"] == "uncategorized"
    assert llm.calls["Job"] == 4
    assert ("tasks", 1, "A", "classification_failed") in error_set(body)


def test_timeout_is_retried_401_is_not(client, workdir, llm):
    llm.script["Job"] = ["timeout", '{"category": "other"}']
    convert(client, tasks=one_task_csv(workdir))
    assert llm.calls["Job"] == 2

    llm.script["Auth"] = [401]
    convert(client, tasks=one_task_csv(workdir, "Auth"))
    assert llm.calls["Auth"] == 1


def test_non_json_then_ok(client, workdir, llm):
    llm.script["Job"] = ["Sure! It's transcription.", '{"category": "transcription"}']
    convert(client, tasks=one_task_csv(workdir))
    assert read_output(workdir)[0]["category"] == "transcription"
    assert llm.calls["Job"] == 2


def test_disallowed_category_twice(client, workdir, llm):
    llm.script["Job"] = ['{"category": "HACKED"}']
    convert(client, tasks=one_task_csv(workdir))
    assert read_output(workdir)[0]["category"] == "uncategorized"
    assert llm.calls["Job"] == 2


def test_missing_key_503(client, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY")
    assert convert(client).status_code == 503


# ---------------------------------------------------------------- Part 3

def big_csv(workdir, n=200, suffix=""):
    lines = ["task_id,title,description,user_id,priority"]
    lines += [f"T{i},Task {i},desc {i}{suffix},U01,1" for i in range(n)]
    (workdir / "data/big.csv").write_text("\n".join(lines) + "\n")
    return "data/big.csv"


def test_concurrency_bounded_and_parallel(client, workdir, llm):
    llm.delay = 0.02
    convert(client, tasks=big_csv(workdir))
    assert llm.max_in_flight <= 10
    assert llm.max_in_flight > 1  # proves it isn't sequential
    rows = read_output(workdir)
    assert [r["task_id"] for r in rows] == [f"T{i}" for i in range(200)]  # input order kept


def test_rerun_makes_zero_calls(client, workdir, llm):
    convert(client, tasks=big_csv(workdir))
    assert llm.total_calls() == 200
    llm.calls.clear()
    convert(client, tasks=big_csv(workdir))
    assert llm.total_calls() == 0


def test_changed_and_failed_rows_are_retried(client, workdir, llm):
    llm.script["Task 0"] = [500]
    convert(client, tasks=big_csv(workdir, n=3))
    llm.calls.clear()
    llm.script.clear()

    path = workdir / "data/big.csv"
    path.write_text(path.read_text().replace("desc 1", "desc 1 changed"))
    convert(client, tasks="data/big.csv")
    assert llm.calls == {"Task 0": 1, "Task 1": 1}  # failed row + changed row; Task 2 cached
