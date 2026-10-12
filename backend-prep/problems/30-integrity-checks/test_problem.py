import copy

from problem_api import load_dataset


def ann(id="A1", **kw):
    return {"id": id, "name": "Ada", "status": "active", "projects": ["P1"], **kw}


def task(id="T1", **kw):
    return {"id": id, "project_id": "P1", "status": "open", "created_at": "2024-03-01T08:00:00Z",
            "completed_at": None, "reward_cents": 100, **kw}


def sub(id="S1", **kw):
    return {"id": id, "task_id": "T1", "annotator_id": "A1", "submitted_at": "2024-03-01T09:00:00Z",
            "confidence": 0.8, "status": "pending", **kw}


def ds(annotators=None, tasks=None, submissions=None):
    return {"annotators": annotators if annotators is not None else [ann()],
            "tasks": tasks if tasks is not None else [task()],
            "submissions": submissions if submissions is not None else [sub()]}


def triples(violations):
    return [(v.entity, v.id, v.rule) for v in violations]


SAMPLE_EXPECTED = [
    ("annotator", "A2", "duplicate"),
    ("annotator", "A3", "bad_status"),
    ("annotator", "A5", "conflicting_duplicate"),
    ("submission", "S1", "duplicate"),
    ("submission", "S10", "bad_confidence"),
    ("submission", "S14", "bad_timestamp"),
    ("submission", "S15", "annotator_not_on_project"),
    ("submission", "S2", "submitted_before_task_created"),
    ("submission", "S3", "unknown_task"),
    ("submission", "S4", "unknown_annotator"),
    ("submission", "S5", "annotator_not_on_project"),
    ("submission", "S6", "bad_confidence"),
    ("submission", "S6", "bad_status"),
    ("submission", "S7", "submitted_before_task_created"),
    ("submission", "S9", "bad_confidence"),
    ("task", "T3", "completed_before_created"),
    ("task", "T4", "bad_reward"),
    ("task", "T4", "bad_status"),
    ("task", "T5", "missing_completed_at"),
    ("task", "T6", "bad_reward"),
    ("task", "T6", "conflicting_duplicate"),
    ("task", "T7", "bad_timestamp"),
    ("task", "T8", "bad_timestamp"),
]


def test_sample_dataset(sol):
    """The sample export yields exactly the expected 23 violations, in order"""
    got = triples(sol.check(load_dataset()))
    missing = [t for t in SAMPLE_EXPECTED if t not in got]
    extra = [t for t in got if t not in SAMPLE_EXPECTED]
    assert not missing and not extra, f"missing: {missing}\nunexpected: {extra}"
    assert got == SAMPLE_EXPECTED, "right violations, wrong order: sort by (entity, id, rule, detail)"


def test_clean_dataset_and_shape(sol):
    """A clean dataset returns []; violations are Violation tuples with a non-empty detail"""
    assert sol.check(ds()) == [], "a fully valid dataset has no violations"
    got = sol.check(ds(submissions=[sub(status="done")]))
    assert len(got) == 1
    v = got[0]
    assert isinstance(v, sol.Violation), "return Violation instances"
    assert (v.entity, v.id, v.rule) == ("submission", "S1", "bad_status")
    assert isinstance(v.detail, str) and v.detail, "detail must be a non-empty string"


def test_enums_and_ranges(sol):
    """bad_status, bad_reward and bad_confidence follow the table (0 and 1 are fine; bools and strings are not)"""
    data = ds(
        annotators=[ann("A1"), ann("A2", status="Active")],
        tasks=[task("T1"), task("T2", reward_cents=0), task("T3", reward_cents=True), task("T4", reward_cents="100"),
               task("T5", reward_cents=-1), task("T6", reward_cents=None), task("T7", status="closed")],
        submissions=[sub("S1", confidence=0), sub("S2", confidence=1), sub("S3", confidence=1.0001),
                     sub("S4", confidence=False), sub("S5", confidence="0.5"), sub("S6", confidence=float("nan")),
                     sub("S7", confidence=-0.1), sub("S8", status="Accepted")],
    )
    assert triples(sol.check(data)) == [
        ("annotator", "A2", "bad_status"),
        ("submission", "S3", "bad_confidence"), ("submission", "S4", "bad_confidence"),
        ("submission", "S5", "bad_confidence"), ("submission", "S6", "bad_confidence"),
        ("submission", "S7", "bad_confidence"), ("submission", "S8", "bad_status"),
        ("task", "T3", "bad_reward"), ("task", "T4", "bad_reward"), ("task", "T5", "bad_reward"),
        ("task", "T6", "bad_reward"), ("task", "T7", "bad_status"),
    ]


def test_referential_integrity(sol):
    """Unknown task/annotator ids are reported; rules that need the missing record are skipped"""
    data = ds(
        annotators=[ann("A1", status="offboarded")],
        tasks=[task("T1", status="weird")],
        submissions=[sub("S1", task_id="T9", submitted_at="2020-01-01T00:00:00Z"),
                     sub("S2", annotator_id="A9"),
                     sub("S3", task_id="T9", annotator_id="A9"),
                     sub("S4")],
    )
    assert triples(sol.check(data)) == [
        ("submission", "S1", "unknown_task"),
        ("submission", "S2", "unknown_annotator"),
        ("submission", "S3", "unknown_annotator"), ("submission", "S3", "unknown_task"),
        ("task", "T1", "bad_status"),
    ], "a record with a bad status still exists; time/project rules need both sides to be known"


def test_compares_instants_not_strings(sol):
    """Timestamps with different offsets are compared as instants; equal instants are not violations"""
    data = ds(
        tasks=[task("T1", created_at="2024-03-01T10:00:00+02:00")],  # 08:00Z
        submissions=[sub("S1", submitted_at="2024-03-01T11:30:00+05:00"),  # 06:30Z: before, though the string is later
                     sub("S2", submitted_at="2024-03-01T09:00:00Z"),       # after, though the string is earlier
                     sub("S3", submitted_at="2024-03-01T08:00:00Z")],      # same instant: fine
    )
    assert triples(sol.check(data)) == [("submission", "S1", "submitted_before_task_created")]


def test_invalid_and_naive_timestamps(sol):
    """Unparseable or naive timestamps are bad_timestamp, and comparisons using them are skipped"""
    data = ds(
        tasks=[task("T1"), task("T2", created_at="2024-03-01T08:00:00"),
               task("T3", status="completed", created_at="soon", completed_at="later"),
               task("T4", created_at=None)],
        submissions=[sub("S1", submitted_at="yesterday"), sub("S2", task_id="T2", submitted_at="2000-01-01T00:00:00Z"),
                     sub("S3", submitted_at=1709290800)],
    )
    assert triples(sol.check(data)) == [
        ("submission", "S1", "bad_timestamp"),
        ("submission", "S3", "bad_timestamp"),
        ("task", "T2", "bad_timestamp"),
        ("task", "T3", "bad_timestamp"), ("task", "T3", "bad_timestamp"),
        ("task", "T4", "bad_timestamp"),
    ], "one bad_timestamp per bad field; no time comparison against an invalid timestamp"


def test_completion_rules(sol):
    """completed_before_created and missing_completed_at follow the table"""
    data = ds(tasks=[
        task("T1", status="completed", completed_at="2024-03-01T07:59:59Z"),
        task("T2", status="completed", completed_at=None),
        task("T3", status="completed", completed_at="2024-03-01T08:00:00Z"),
        task("T4", status="cancelled", completed_at="2024-03-01T09:00:00+02:00"),
        task("T5", status="open"),
    ], submissions=[])
    assert triples(sol.check(data)) == [
        ("task", "T1", "completed_before_created"),
        ("task", "T2", "missing_completed_at"),
        ("task", "T4", "completed_before_created"),
    ], "T3 completes at the creation instant (fine); T4's 09:00+02:00 is 07:00Z"


def test_project_assignment(sol):
    """A submission by an annotator not assigned to the task's project is annotator_not_on_project"""
    data = ds(
        annotators=[ann("A1", projects=["P1", "P2"]), ann("A2", projects=["P2"]), ann("A3", projects=[])],
        tasks=[task("T1", project_id="P1"), task("T2", project_id="P2")],
        submissions=[sub("S1", annotator_id="A1"), sub("S2", annotator_id="A2"),
                     sub("S3", annotator_id="A2", task_id="T2"), sub("S4", annotator_id="A3", task_id="T2")],
    )
    assert triples(sol.check(data)) == [
        ("submission", "S2", "annotator_not_on_project"),
        ("submission", "S4", "annotator_not_on_project"),
    ]


def test_duplicates_first_occurrence_wins(sol):
    """Duplicates are reported once per id; other rules and lookups use the first copy only"""
    data = ds(
        annotators=[ann("A1", projects=["P1"]), ann("A1", projects=["P1", "P2"])],
        tasks=[task("T1"), task("T1"), task("T1"), task("T2", project_id="P2", reward_cents=-5),
               task("T2", project_id="P2", reward_cents=5)],
        submissions=[sub("S1", task_id="T2", status="x"), sub("S1", task_id="T2", status="x")],
    )
    assert triples(sol.check(data)) == [
        ("annotator", "A1", "conflicting_duplicate"),
        ("submission", "S1", "annotator_not_on_project"),
        ("submission", "S1", "bad_status"),
        ("submission", "S1", "duplicate"),
        ("task", "T1", "duplicate"),
        ("task", "T2", "bad_reward"),
        ("task", "T2", "conflicting_duplicate"),
    ], "3 identical T1s are one 'duplicate'; A1's first copy (P1 only) is the one used for S1's project check"


def test_does_not_mutate_input(sol):
    """check() leaves the dataset unchanged"""
    data = load_dataset()
    before = copy.deepcopy(data)
    sol.check(data)
    assert data == before, "check() must not modify, sort or dedupe the input in place"
