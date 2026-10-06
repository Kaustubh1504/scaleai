import json
import os

import pytest

from dispatcher.state import AuditLog, DeliveryStore, StateError, write_json_atomic


def test_round_trip(tmp_path):
    store = DeliveryStore(tmp_path / "deliveries.json")
    assert store.load() == {}
    record = {"event_id": "e|1", "subscription_id": "s", "status": "pending", "attempts": 2,
              "next_attempt_at": 1700000012.345678, "last_error": "HTTP 503"}
    store.save([record])
    assert store.load() == {("e|1", "s"): record}


def test_failed_write_keeps_previous_file_and_no_temp_files(tmp_path, monkeypatch):
    path = tmp_path / "deliveries.json"
    write_json_atomic(path, {"v": 1})

    def boom(src, dst):
        raise OSError("disk full")

    monkeypatch.setattr(os, "replace", boom)
    with pytest.raises(OSError):
        write_json_atomic(path, {"v": 2})
    assert json.loads(path.read_text()) == {"v": 1}
    assert [p.name for p in tmp_path.iterdir()] == ["deliveries.json"]


@pytest.mark.parametrize("content", ["{not json", "[]", '{"version": 99, "deliveries": []}',
                                     '{"version": 1, "deliveries": [{"event_id": "e"}]}'])
def test_unreadable_state_refuses_to_start(tmp_path, content):
    path = tmp_path / "deliveries.json"
    path.write_text(content)
    with pytest.raises(StateError):
        DeliveryStore(path).load()


def test_audit_log_appends(tmp_path):
    log = AuditLog(tmp_path / "audit.jsonl")
    log.append({"a": 1})
    AuditLog(tmp_path / "audit.jsonl").append({"a": "é"})
    assert [json.loads(line) for line in (tmp_path / "audit.jsonl").read_text().splitlines()] == [{"a": 1}, {"a": "é"}]
