from app.models import parse_entry


def test_valid_entry():
    task, error = parse_entry({"id": "t-1", "data": {"x": 1}, "labels": ["a", "b"], "gold_label": "b", "extra": 1})
    assert error is None
    assert (task.id, task.labels, task.gold_label) == ("t-1", ["a", "b"], "b")


def test_invalid_entries_report_a_message():
    for entry in [
        {"data": {}, "labels": []},
        {"data": {}, "labels": ["a", "a"]},
        {"data": {}, "labels": ["a", " "]},
        {"data": "text", "labels": ["a"]},
        {"id": "../x", "data": {}, "labels": ["a"]},
        {"data": {}, "labels": ["a"], "gold_label": "b"},
        {"labels": ["a"]},
        "not an object",
    ]:
        task, error = parse_entry(entry)
        assert task is None and error, entry
