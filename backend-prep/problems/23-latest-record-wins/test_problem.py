import copy

from problem_api import STREAM


def ev(id, version, updated_at, deleted=False, **fields):
    return {"id": id, "version": version, "updated_at": updated_at, "deleted": deleted, **fields}


def by_id(records):
    return {r["id"]: r for r in records}


def test_sample_stream(sol):
    """The sample stream materializes to 4 tasks and 1 conflict"""
    records, conflicts = sol.materialize(STREAM)
    assert records == [
        {"id": "task_2", "version": 2, "updated_at": "2024-05-01T09:30:00Z", "status": "in_progress", "assignee": "ann_7"},
        {"id": "task_3", "version": 2, "updated_at": "2024-05-01T12:00:00Z", "status": "in_progress", "assignee": "ann_2"},
        {"id": "task_5", "version": 1, "updated_at": "2024-05-01T11:00:00Z", "status": "queued", "assignee": None},
        {"id": "task_7", "version": 4, "updated_at": "2024-05-02T00:00:00Z", "status": "rejected", "assignee": "ann_1"},
    ]
    assert conflicts == [{"id": "task_7", "version": 4, "updated_at": "2024-05-02T00:00:00Z"}]


def test_newest_instant_wins_over_version(sol):
    """The latest updated_at wins even when its version is lower"""
    records, _ = sol.materialize([ev("t", 3, "2024-05-01T09:15:00Z", status="c"),
                                  ev("t", 2, "2024-05-01T09:30:00Z", status="b"),
                                  ev("t", 1, "2024-05-01T09:00:00Z", status="a")])
    assert records[0]["status"] == "b" and records[0]["version"] == 2


def test_offsets_compared_as_instants(sol):
    """Offsets are compared as UTC instants, not as strings"""
    # As strings "10:30+02:00" > "09:00Z", but 10:30+02:00 is 08:30Z, which is earlier.
    records, _ = sol.materialize([ev("t", 1, "2024-05-01T09:00:00Z", status="utc"),
                                  ev("t", 2, "2024-05-01T10:30:00+02:00", status="cest")])
    assert records[0]["status"] == "utc", "10:30+02:00 is 08:30Z, earlier than 09:00Z"
    records, _ = sol.materialize([ev("t", 1, "2024-05-01T23:00:00-05:00", status="late"),
                                  ev("t", 2, "2024-05-02T03:00:00Z", status="early")])
    assert records[0]["status"] == "late", "23:00-05:00 is 04:00Z the next day"


def test_same_instant_higher_version_wins(sol):
    """Same updated_at instant: the higher version wins, regardless of arrival order"""
    records, conflicts = sol.materialize([ev("t", 5, "2024-05-01T12:00:00Z", status="v5"),
                                          ev("t", 4, "2024-05-01T14:00:00+02:00", status="v4")])
    assert records[0]["version"] == 5 and records[0]["status"] == "v5"
    assert conflicts == [], "different versions at one instant are not a conflict"


def test_tombstone_removes_id(sol):
    """A newest tombstone removes the id; an older tombstone is ignored"""
    records, _ = sol.materialize([ev("gone", 1, "2024-05-01T08:00:00Z", status="queued"),
                                  ev("gone", 2, "2024-05-01T10:00:00Z", deleted=True),
                                  ev("kept", 2, "2024-05-01T08:00:00Z", deleted=True),
                                  ev("kept", 1, "2024-05-01T09:00:00Z", status="live")])
    assert [r["id"] for r in records] == ["kept"], "'gone' was deleted last; 'kept' was recreated after its tombstone"
    assert records[0]["status"] == "live"


def test_resurrection_after_delete(sol):
    """A live version newer than a tombstone brings the id back"""
    records, _ = sol.materialize([ev("t", 1, "2024-05-01T08:00:00Z", status="a"),
                                  ev("t", 2, "2024-05-01T09:00:00Z", deleted=True),
                                  ev("t", 3, "2024-05-01T10:00:00Z", status="back")])
    assert records == [{"id": "t", "version": 3, "updated_at": "2024-05-01T10:00:00Z", "status": "back"}]


def test_output_shape_and_order(sol):
    """Records sorted by id as strings, deleted key dropped, updated_at in UTC Z format"""
    records, _ = sol.materialize([ev("task_9", 1, "2024-05-01T08:00:00+05:30", priority=2),
                                  ev("task_10", 1, "2024-05-01T08:00:00Z", priority=1),
                                  {"id": "task_1", "version": 1, "updated_at": "2024-05-01T08:00:00Z", "priority": 3}])
    assert [r["id"] for r in records] == ["task_1", "task_10", "task_9"], "plain string order"
    assert all("deleted" not in r for r in records), "drop the deleted key from output records"
    assert by_id(records)["task_9"]["updated_at"] == "2024-05-01T02:30:00Z"
    assert by_id(records)["task_9"]["priority"] == 2, "other fields are kept as-is"


def test_identical_duplicates_are_not_conflicts(sol):
    """Identical duplicates (even with differently-spelled timestamps) are not conflicts"""
    records, conflicts = sol.materialize([ev("t", 2, "2024-05-01T12:00:00Z", status="x"),
                                          ev("t", 2, "2024-05-01T14:00:00+02:00", status="x"),
                                          {"id": "t", "version": 2, "updated_at": "2024-05-01T12:00:00+00:00",
                                           "status": "x"}])
    assert conflicts == [], "same content, same instant, same version is just a duplicate; missing deleted == False"
    assert len(records) == 1


def test_conflict_reported_and_later_wins(sol):
    """Same id, instant and version with different content: a conflict, and the later event wins"""
    records, conflicts = sol.materialize([ev("t", 4, "2024-05-02T00:00:00Z", status="accepted"),
                                          ev("t", 4, "2024-05-02T02:00:00+02:00", status="rejected")])
    assert conflicts == [{"id": "t", "version": 4, "updated_at": "2024-05-02T00:00:00Z"}]
    assert records[0]["status"] == "rejected", "on an exact tie the event later in the input wins"
    _, conflicts = sol.materialize([ev("t", 1, "2024-05-02T00:00:00Z", status="x"),
                                    ev("t", 1, "2024-05-02T00:00:00Z", deleted=True, status="x")])
    assert len(conflicts) == 1, "deleted differs, so the content differs"


def test_superseded_conflicts_sorted(sol):
    """Conflicts are reported even when superseded, sorted by (id, updated_at, version)"""
    _, conflicts = sol.materialize([
        ev("b", 1, "2024-05-01T10:00:00Z", s=1), ev("b", 1, "2024-05-01T10:00:00Z", s=2),
        ev("a", 3, "2024-05-01T09:00:00Z", s=1), ev("a", 3, "2024-05-01T09:00:00Z", s=2),
        ev("a", 2, "2024-05-01T08:00:00Z", s=1), ev("a", 2, "2024-05-01T08:00:00Z", s=2),
        ev("a", 9, "2024-05-03T00:00:00Z", s=9),
    ])
    assert conflicts == [{"id": "a", "version": 2, "updated_at": "2024-05-01T08:00:00Z"},
                         {"id": "a", "version": 3, "updated_at": "2024-05-01T09:00:00Z"},
                         {"id": "b", "version": 1, "updated_at": "2024-05-01T10:00:00Z"}]


def test_empty_and_no_mutation(sol):
    """Empty input gives ([], []); input events are never modified"""
    assert sol.materialize([]) == ([], [])
    before = copy.deepcopy(STREAM)
    sol.materialize(STREAM)
    assert STREAM == before, "don't pop 'deleted' or rewrite updated_at on the caller's dicts"
