import copy
import csv
import io

import pytest

from problem_api import load_tasks


def parse(text):
    return list(csv.reader(io.StringIO(text)))


def drop_empty(value):
    """What flatten -> unflatten should give back: x with empty dicts/lists removed."""
    if isinstance(value, dict):
        out = {k: drop_empty(v) for k, v in value.items()}
        return {k: v for k, v in out.items() if v != {} and v != []}
    if isinstance(value, list):
        return [drop_empty(v) for v in value]
    return value


def test_flatten_nested_dicts(sol):
    """Nested dicts become dotted keys, depth-first in insertion order"""
    got = sol.flatten({"id": "t-1", "project": {"id": "p-9", "owner": {"name": "Ana"}}, "status": "done"})
    assert got == {"id": "t-1", "project.id": "p-9", "project.owner.name": "Ana", "status": "done"}
    assert list(got) == ["id", "project.id", "project.owner.name", "status"], "keys must be in depth-first order"


def test_flatten_lists(sol):
    """Lists are indexed; lists of dicts and lists of lists recurse"""
    got = sol.flatten({
        "tags": ["night", "rain"],
        "annotations": [{"label": "stop", "bbox": [1, 2]}, {"label": "yield"}],
        "grid": [[1, 2], [3]],
    })
    assert got == {
        "tags.0": "night", "tags.1": "rain",
        "annotations.0.label": "stop", "annotations.0.bbox.0": 1, "annotations.0.bbox.1": 2,
        "annotations.1.label": "yield",
        "grid.0.0": 1, "grid.0.1": 2, "grid.1.0": 3,
    }


def test_flatten_leaves_and_empties(sol):
    """None/bool/number leaves are kept as is; empty dicts and lists are omitted"""
    src = {"reviewer": None, "flagged": False, "conf": 0.98, "n": 0, "meta": {}, "tags": [], "deep": {"x": {}, "y": []}}
    assert sol.flatten(src) == {"reviewer": None, "flagged": False, "conf": 0.98, "n": 0}
    assert sol.flatten({}) == {}


def test_flatten_bad_keys_and_input(sol):
    """A key containing sep (or empty) raises ValueError; a non-dict raises TypeError; input isn't mutated"""
    with pytest.raises(ValueError):
        sol.flatten({"meta": {"model.version": "v2"}})
    with pytest.raises(ValueError):
        sol.flatten({"": 1})
    assert sol.flatten({"model.version": "v2"}, sep="/") == {"model.version": "v2"}, "'.' is fine when sep is '/'"
    assert sol.flatten({"a": {"b": 1}}, sep="/") == {"a/b": 1}
    with pytest.raises(TypeError):
        sol.flatten([{"a": 1}])
    tasks = load_tasks()
    before = copy.deepcopy(tasks)
    for t in tasks:
        sol.flatten(t)
    assert tasks == before, "flatten must not modify its input"


def test_csv_columns_first_seen_union(sol):
    """CSV columns are the union of keys in first-seen order; missing cells are empty"""
    rows = parse(sol.to_csv_text(load_tasks()))
    header = rows[0]
    assert header[:4] == ["task_id", "project.id", "project.name", "status"]
    assert header[-4:] == ["reviewer.id", "reviewer.note", "flagged", "annotations.0.text"], (
        "columns first seen in later records go at the end, in the order they appear"
    )
    assert len(header) == 23 and len(set(header)) == 23
    assert len(rows) == 4 and all(len(r) == 23 for r in rows), "every row has a cell for every column"
    t2 = dict(zip(header, rows[2]))
    assert t2["annotations.0.label"] == "" and t2["tags.0"] == "blurry" and t2["flagged"] == "true"
    assert "meta" not in header, "an empty {} makes no column"


def test_csv_quoting(sol):
    """Commas, quotes and newlines survive a csv.reader round trip"""
    rows = parse(sol.to_csv_text(load_tasks()))
    cells = {c for r in rows for c in r}
    assert 'Too blurry, "unusable"' in cells
    assert "Receipts, scanned" in cells
    assert "$12.50\nincl. tax" in cells, "a newline inside a value must be quoted, not split into two rows"


def test_csv_exact_text(sol):
    """Exact output: header, \\n line endings, None -> '', bools -> true/false"""
    text = sol.to_csv_text([{"id": 1, "ok": True, "who": None}, {"id": 2, "note": "a, b", "ok": False}])
    assert text == 'id,ok,who,note\n1,true,,\n2,false,,"a, b"\n'
    assert sol.to_csv_text([]) == ""


def test_unflatten_basic(sol):
    """unflatten rebuilds dicts and lists (list indexes in any order)"""
    assert sol.unflatten({"a.1": "y", "a.0": "x", "b.c": None, "d": 3}) == {"a": ["x", "y"], "b": {"c": None}, "d": 3}
    assert sol.unflatten({"spans.0.start": 0, "spans.0.label": "PER", "spans.1.start": 5}) == {
        "spans": [{"start": 0, "label": "PER"}, {"start": 5}]
    }
    assert sol.unflatten({"m.0.1": "b", "m.0.0": "a"}) == {"m": [["a", "b"]]}
    assert sol.unflatten({"a.01": 1}) == {"a": {"01": 1}}, "'01' isn't a canonical index, so it's a dict key"
    assert sol.unflatten({"a/b": 1, "a/c.d": 2}, sep="/") == {"a": {"b": 1, "c.d": 2}}


def test_round_trip_sample(sol):
    """unflatten(flatten(task)) gives back every sample task (minus empty containers)"""
    for task in load_tasks():
        assert sol.unflatten(sol.flatten(task)) == drop_empty(task), f"round trip failed for {task['task_id']}"


def test_unflatten_errors(sol):
    """Gaps in indexes, mixed index/key children, leaf-vs-prefix conflicts and empty segments raise ValueError"""
    bad = [
        {"a.0": 1, "a.2": 2},
        {"a.1": 1},
        {"a.0": 1, "a.x": 2},
        {"a": 1, "a.b": 2},
        {"a.b": 2, "a": 1},
        {"a..b": 1},
        {"a.": 1},
    ]
    for flat in bad:
        try:
            sol.unflatten(flat)
        except ValueError:
            continue
        pytest.fail(f"unflatten({flat!r}) should raise ValueError")
