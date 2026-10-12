import pytest

from problem_api import sample_text

FENCE = "```"


def lines(*items):
    return "\n".join(items) + "\n"


def one(sol, text):
    records, errors = sol.parse_jsonl(text)
    assert errors == [], f"unexpected errors: {errors}"
    assert len(records) == 1, f"expected one record, got {records}"
    return records[0]


def reasons(sol, text):
    records, errors = sol.parse_jsonl(text)
    return records, [e["reason"] for e in errors]


def test_sample_records(sol):
    """The sample log yields the 5 recoverable records, normalized, in file order"""
    records, _ = sol.parse_jsonl(sample_text())
    assert records == [
        {"user_id": "u1", "label": "positive", "score": 0.9},
        {"user_id": "u2", "label": "neutral", "score": 0.75},
        {"user_id": "u3", "label": "positive", "score": pytest.approx(0.9)},
        {"user_id": "u5", "label": "positive", "score": 1.0},
        {"user_id": "10", "label": "neutral", "score": None},
    ]


def test_sample_errors(sol):
    """The sample log reports each bad record at its line with the right reason"""
    _, errors = sol.parse_jsonl(sample_text())
    assert errors == [
        {"line": 5, "reason": "invalid_json"},
        {"line": 11, "reason": "not_object"},
        {"line": 12, "reason": "not_object"},
        {"line": 13, "reason": "conflicting_user_id"},
        {"line": 14, "reason": "missing_user_id"},
        {"line": 15, "reason": "invalid_score"},
        {"line": 16, "reason": "invalid_score"},
        {"line": 18, "reason": "invalid_json"},
        {"line": 19, "reason": "unclosed_fence"},
    ]


def test_user_id_aliases(sol):
    """userId / uid become user_id; alias keys are removed; ints become strings; strings are stripped"""
    assert one(sol, '{"userId": "a", "x": 1}\n') == {"user_id": "a", "x": 1, "score": None}
    assert one(sol, '{"uid": 42}\n') == {"user_id": "42", "score": None}
    assert one(sol, '{"user_id": " u1 "}\n')["user_id"] == "u1"
    assert one(sol, '{"uid": 7, "user_id": "7"}\n')["user_id"] == "7", "7 and '7' agree after normalizing"
    assert one(sol, '{"uid": null, "userId": "b"}\n')["user_id"] == "b", "a null alias counts as absent"


def test_user_id_errors(sol):
    """Missing, invalid and conflicting user ids are reported with the right reason"""
    text = lines(
        '{"label": "x"}',
        '{"user_id": null}',
        '{"user_id": true}',
        '{"uid": ""}',
        '{"uid": ["u1"]}',
        '{"user_id": "u1", "userId": "u2"}',
    )
    records, got = reasons(sol, text)
    assert records == []
    assert got == ["missing_user_id", "missing_user_id", "invalid_user_id", "invalid_user_id",
                   "invalid_user_id", "conflicting_user_id"]


def test_score_forms(sol):
    """score accepts 0.9, 1, "0.75", " 85% ", "1e-1"; missing or null is None"""
    cases = [("0.9", 0.9), ("1", 1.0), ('"0.75"', 0.75), ('" 85% "', 0.85), ('"1e-1"', 0.1), ("0", 0.0), ("null", None)]
    for raw, expected in cases:
        rec = one(sol, f'{{"user_id": "u", "score": {raw}}}\n')
        if expected is None:
            assert rec["score"] is None, f"score {raw} -> None"
        else:
            assert rec["score"] == pytest.approx(expected) and type(rec["score"]) is float, f"score {raw} -> {expected} (float)"
    assert one(sol, '{"user_id": "u"}\n')["score"] is None, "a missing score is present in the output as None"


def test_invalid_scores(sol):
    """Scores that aren't a number in [0, 1] are invalid_score (bools, NaN, 120%, words, lists)"""
    bad = ['"high"', '"120%"', "-0.1", "1.01", "true", '"nan"', "NaN", "[0.5]", '""', '"%"']
    text = lines(*(f'{{"user_id": "u", "score": {b}}}' for b in bad))
    records, got = reasons(sol, text)
    assert records == [], f"these should all be rejected, got {records}"
    assert got == ["invalid_score"] * len(bad)


def test_one_line_fences(sol):
    """One-line fenced JSON is recovered, with or without the json tag (any case)"""
    text = lines(
        FENCE + 'json {"uid": "a", "score": 0.1} ' + FENCE,
        FENCE + '{"uid": "b"}' + FENCE,
        "   " + FENCE + 'JSON   {"uid": "c"}   ' + FENCE + "  ",
    )
    records, errors = sol.parse_jsonl(text)
    assert errors == []
    assert [r["user_id"] for r in records] == ["a", "b", "c"]


def test_multi_line_fence(sol):
    """A multi-line fenced block is one record reported at the opener's line; parsing resumes after it"""
    text = lines(
        '{"uid": "a"}',            # 1
        FENCE + "JSON",            # 2
        "{",                       # 3
        '  "uid": "b",',           # 4
        "",                        # 5
        '  "score": "50%"',        # 6
        "}",                       # 7
        FENCE,                     # 8
        FENCE,                     # 9  opener
        '{"uid": "c",}',           # 10
        FENCE,                     # 11
        '{"uid": "d"}',            # 12
    )
    records, errors = sol.parse_jsonl(text)
    assert [r["user_id"] for r in records] == ["a", "b", "d"]
    assert records[1]["score"] == pytest.approx(0.5)
    assert errors == [{"line": 9, "reason": "invalid_json"}], "a bad block is reported once, at its opener line"


def test_unclosed_fence_stops(sol):
    """An unclosed fence is reported at the opener and swallows the rest of the text"""
    text = lines('{"uid": "a"}', FENCE + "json", '{"uid": "b"}', '{"uid": "c"}')
    records, errors = sol.parse_jsonl(text)
    assert [r["user_id"] for r in records] == ["a"]
    assert errors == [{"line": 2, "reason": "unclosed_fence"}]


def test_invalid_json_not_repaired(sol):
    """Trailing commas, single quotes and truncated objects are invalid_json (never repaired)"""
    text = lines('{"uid": "a",}', "{'uid': 'b'}", '{"uid": "c"', "not json at all")
    records, got = reasons(sol, text)
    assert records == []
    assert got == ["invalid_json"] * 4


def test_non_objects(sol):
    """Valid JSON that isn't an object (list, number, string, null) is not_object"""
    records, got = reasons(sol, lines("[1, 2]", "42", '"u1"', "null"))
    assert records == []
    assert got == ["not_object"] * 4


def test_blank_lines_crlf_and_empty(sol):
    """Blank lines and CRLF endings are fine; line numbers still count blank lines; '' gives ([], [])"""
    text = '\r\n  \r\n{"uid": "a"}\r\n\r\n{oops\r\n'
    records, errors = sol.parse_jsonl(text)
    assert [r["user_id"] for r in records] == ["a"]
    assert errors == [{"line": 5, "reason": "invalid_json"}]
    assert sol.parse_jsonl("") == ([], [])
