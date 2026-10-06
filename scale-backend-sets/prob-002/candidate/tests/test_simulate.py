from lb.simulate import load_tasks


def test_load_tasks_skips_malformed_lines(tmp_path):
    path = tmp_path / "tasks.jsonl"
    path.write_text('{"id": "a", "priority": 2}\n\nnot json\n{"id": 7}\n{"id": "b", "priority": "x"}\n[1]\n'
                    '{"id": "c", "payload": {"k": 1}}\n')
    tasks = load_tasks(path)
    assert [(t.id, t.priority, t.payload) for t in tasks] == [("a", 2, {"id": "a"}), ("c", 0, {"k": 1})]
