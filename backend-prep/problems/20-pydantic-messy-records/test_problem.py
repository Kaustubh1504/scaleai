from datetime import datetime, timezone

from problem_api import RAW_RECORDS

UTC = timezone.utc


def base(**overrides):
    rec = {"id": "ann_1", "email": "a@example.com", "joined_at": "2024-03-01T10:00:00Z"}
    rec.update(overrides)
    return rec


def one(sol, **overrides):
    """Parse a single record; return (annotator or None, error or None)."""
    valid, errors = sol.parse_records([base(**overrides)])
    assert len(valid) + len(errors) == 1, "every input item must end up in exactly one of the two lists"
    return (valid[0] if valid else None), (errors[0] if errors else None)


def field_of(sol, **overrides):
    a, err = one(sol, **overrides)
    assert err is not None, f"expected {overrides} to be rejected, got {a!r}"
    return err["field"]


def test_sample_batch(sol):
    """The sample batch: 3 valid annotators and 6 errors with the right index and field"""
    valid, errors = sol.parse_records(RAW_RECORDS)
    assert all(isinstance(a, sol.Annotator) for a in valid), "valid items must be Annotator instances"
    assert [a.id for a in valid] == ["ann_101", "ann_102", "ann_109"]
    assert [(e["index"], e["field"]) for e in errors] == [
        (2, "email"), (3, "age"), (4, "id"), (5, "age"), (6, None), (7, "joined_at")]
    assert all(isinstance(e["message"], str) and e["message"] for e in errors), "message must be a non-empty str"


def test_id_rules(sol):
    """id is stripped; blank or non-string ids are rejected"""
    a, _ = one(sol, id="  ann_7 ")
    assert a.id == "ann_7"
    assert field_of(sol, id="   ") == "id"
    assert field_of(sol, id=7) == "id", "an int id is not a string"


def test_email_rules(sol):
    """email is stripped and lower-cased; addresses without a dotted domain are rejected"""
    a, _ = one(sol, email="  Mei.Lin@Example.COM ")
    assert a.email == "mei.lin@example.com"
    for bad in ("mei@example", "no-at-sign.com", "a b@example.com", ""):
        assert field_of(sol, email=bad) == "email", f"{bad!r} should be rejected"


def test_age_accepts(sol):
    """age accepts 42, "42", " 42 ", and treats missing / None / "" as None"""
    assert one(sol, age=42)[0].age == 42
    assert one(sol, age="42")[0].age == 42
    assert one(sol, age=" 42 ")[0].age == 42
    assert one(sol)[0].age is None, "age is optional"
    assert one(sol, age=None)[0].age is None
    assert one(sol, age="")[0].age is None


def test_age_rejects(sol):
    """age rejects True, 42.5, "42.5", "abc", and anything outside 16..99"""
    for bad in (True, False, 42.5, 42.0, "42.5", "abc", 15, 100, "-20"):
        assert field_of(sol, age=bad) == "age", f"age={bad!r} should be rejected"
    assert one(sol, age=16)[0].age == 16 and one(sol, age="99")[0].age == 99, "16 and 99 are allowed"


def test_tags(sol):
    """tags from "a, b" or a list: stripped, lower-cased, blanks dropped, deduped in order"""
    assert one(sol, tags="NER, sentiment, ner,  ,OCR")[0].tags == ["ner", "sentiment", "ocr"]
    assert one(sol, tags=[" Audio", "audio", "RLHF", ""])[0].tags == ["audio", "rlhf"]
    assert one(sol, tags=None)[0].tags == []
    assert one(sol)[0].tags == []
    assert field_of(sol, tags=["ok", 3]) == "tags", "a non-string tag is an error"
    assert field_of(sol, tags=5) == "tags"


def test_joined_at_timezones(sol):
    """joined_at with Z, an offset, or no offset all become aware UTC datetimes"""
    cases = {
        "2024-03-01T10:00:00Z": datetime(2024, 3, 1, 10, 0, tzinfo=UTC),
        "2024-03-01T12:30:00+02:00": datetime(2024, 3, 1, 10, 30, tzinfo=UTC),
        "2024-03-01T23:00:00-05:00": datetime(2024, 3, 2, 4, 0, tzinfo=UTC),
        "2024-03-01T10:00:00": datetime(2024, 3, 1, 10, 0, tzinfo=UTC),
    }
    for raw, expected in cases.items():
        got = one(sol, joined_at=raw)[0].joined_at
        assert got.tzinfo is not None, f"{raw!r}: joined_at must be timezone-aware"
        assert got == expected and got.utcoffset().total_seconds() == 0, \
            f"{raw!r} should be {expected.isoformat()} in UTC, got {got.isoformat()}"


def test_joined_at_rejects(sol):
    """joined_at rejects unparseable strings and non-strings (no unix timestamps)"""
    for bad in ("yesterday", "2024-13-01T00:00:00Z", 1709287200, None):
        assert field_of(sol, joined_at=bad) == "joined_at", f"joined_at={bad!r} should be rejected"


def test_required_fields_and_unknown_keys(sol):
    """Missing required fields are reported by name; unknown keys are ignored"""
    valid, errors = sol.parse_records([{"email": "a@example.com", "joined_at": "2024-03-01T10:00:00Z"},
                                       {"id": "x", "joined_at": "2024-03-01T10:00:00Z"},
                                       {"id": "x", "email": "a@example.com"}])
    assert [e["field"] for e in errors] == ["id", "email", "joined_at"]
    a, err = one(sol, referrer="campus", score=9)
    assert err is None and a is not None, "unknown keys must not cause an error"


def test_first_failing_field_only(sol):
    """One error per record: the first failing field in order id, email, age, tags, joined_at"""
    _, errors = sol.parse_records([
        {"id": "", "email": "bad", "age": True, "joined_at": "never"},
        {"id": "ok", "email": "bad", "age": True, "joined_at": "never"},
        {"id": "ok", "email": "a@example.com", "age": "x", "tags": [1], "joined_at": "never"},
        {"id": "ok", "email": "a@example.com", "tags": [1], "joined_at": "never"},
    ])
    assert [e["field"] for e in errors] == ["id", "email", "age", "tags"]
    assert [e["index"] for e in errors] == [0, 1, 2, 3]


def test_non_dict_items(sol):
    """Items that aren't dicts (a string, None, a list) are errors with field None, never a crash"""
    valid, errors = sol.parse_records(["ann_107,fatima@example.com,30", None, [1, 2], base()])
    assert len(valid) == 1
    assert errors == [{"index": i, "field": None, "message": errors[i]["message"]} for i in range(3)]
    assert sol.parse_records([]) == ([], [])
