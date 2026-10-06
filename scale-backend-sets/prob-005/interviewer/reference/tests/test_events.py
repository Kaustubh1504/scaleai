from pathlib import Path

from dispatcher.events import Event, EventStore

DATA = Path(__file__).resolve().parents[3] / "candidate" / "data"


def test_sample_file_skips_and_reports_bad_lines():
    scan = EventStore(DATA / "events.jsonl").scan()
    assert [e.id for e in scan.events] == ["evt_0001", "evt_0002", "evt_0004", "evt_0005", "evt_0008", "evt_0009"]
    # 3: truncated JSON, 7: array, 8: no data, 9: duplicate id, 11: empty id. Line 5 is blank (ignored).
    assert scan.skipped_lines == [3, 7, 8, 9, 11]
    assert scan.events[4].data["project"] == "café-reviews ☕"


def test_duplicate_of_invalid_line_is_not_a_duplicate(tmp_path):
    path = tmp_path / "events.jsonl"
    path.write_text('{"id": "e1", "type": "t"}\n'
                    '{"id": "e1", "type": "t", "created_at": "x", "data": {}}\n'
                    '{"id": "e1", "type": "t", "created_at": "y", "data": {}}\n')
    scan = EventStore(path).scan()
    assert [(e.id, e.created_at) for e in scan.events] == [("e1", "x")]
    assert scan.skipped_lines == [1, 3]


def test_missing_file_is_empty_and_append_round_trips(tmp_path):
    store = EventStore(tmp_path / "events.jsonl")
    assert store.scan().events == [] and store.read() == []
    store.append(Event("e1", "task.completed", "2024-01-01T00:00:00Z", {"k": [1, 2]}))
    assert store.read() == [Event("e1", "task.completed", "2024-01-01T00:00:00Z", {"k": [1, 2]})]


def test_invalid_utf8_line_is_skipped_not_fatal(tmp_path):
    path = tmp_path / "events.jsonl"
    path.write_bytes(b'\xff\xfe garbage\n{"id": "e1", "type": "t", "created_at": "x", "data": {}}\n')
    scan = EventStore(path).scan()
    assert [e.id for e in scan.events] == ["e1"] and scan.skipped_lines == [1]
