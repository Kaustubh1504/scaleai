import pytest

from problem_api import PAYOUTS, REQUIRED


def write(tmp_path, text, *, bom=False):
    p = tmp_path / "payouts.csv"
    p.write_bytes((b"\xef\xbb\xbf" if bom else b"") + text.encode("utf-8"))
    return p


def test_sample_rows(sol):
    """The sample file yields exactly the 5 good rows, in file order"""
    res = sol.load_rows(PAYOUTS, REQUIRED)
    got = [r["annotator_id"] for r in res.rows]
    assert got == ["ann_01", "ann_02", "ann_03", "ann_06", "ann_08"], f"got rows for {got}"


def test_multiline_note_preserved(sol):
    """A quoted note spanning 3 lines (with \"\" escapes) stays one value"""
    res = sol.load_rows(PAYOUTS, REQUIRED)
    by_id = {r["annotator_id"]: r for r in res.rows}
    assert by_id["ann_03"]["note"] == 'Reviewer said:\n"redo spans 4-7"\nthen approved'
    assert by_id["ann_06"]["note"] == "multi\nline"


def test_sample_errors_with_physical_lines(sol):
    """Errors carry the physical line where the record starts (multi-line records count every line)"""
    res = sol.load_rows(PAYOUTS, REQUIRED)
    assert res.errors == [
        {"line": 9, "reason": "too_few_fields"},
        {"line": 10, "reason": "too_many_fields"},
        {"line": 12, "reason": "missing_required"},
        {"line": 19, "reason": "missing_required"},
    ], "lines 7-8 are inside ann_03's note: counting records instead of lines puts these off by 2"


def test_junk_is_silent(sol):
    """Comments, the repeated header and TOTAL / 'Exported N rows' footers are neither rows nor errors"""
    res = sol.load_rows(PAYOUTS, REQUIRED)
    junk_lines = {1, 2, 13, 14, 15, 16, 21, 22}
    assert not junk_lines & {e["line"] for e in res.errors}, "junk lines must be skipped silently, not reported"
    ids = {r["annotator_id"] for r in res.rows}
    assert not ids & {"annotator_id", "TOTAL", "Exported 6 rows", "Exported 3 rows"}, "junk leaked into rows"


def test_values_stripped(sol):
    """Header names and values are stripped"""
    res = sol.load_rows(PAYOUTS, REQUIRED)
    assert res.rows[-1] == {"annotator_id": "ann_08", "task_id": "t-108", "hours": "1.0",
                            "amount_usd": "15.00", "note": "padded"}


def test_line_numbers_with_blank_lines_and_bom(sol, tmp_path):
    """Line numbers count blank lines, comments and multi-line fields (BOM file)"""
    text = (
        "\n"                          # 1
        "# exported by ops\n"         # 2
        "id,amount,note\n"            # 3
        '1,10,"a\n'                   # 4
        'b"\n'                        # 5
        "\n"                          # 6
        "2,,x\n"                      # 7  missing_required
        '3,30,"c\n'                   # 8
        "d\n"                         # 9
        'e"\n'                        # 10
        "4,40\n"                      # 11 too_few_fields
    )
    res = sol.load_rows(write(tmp_path, text, bom=True), ["id", "amount"])
    assert [r["id"] for r in res.rows] == ["1", "3"], "the BOM must not end up in the first header name"
    assert res.errors == [{"line": 7, "reason": "missing_required"}, {"line": 11, "reason": "too_few_fields"}]


def test_field_count_checked_before_required(sol, tmp_path):
    """A ragged record reports the field-count reason even if a required value is also empty"""
    text = "id,amount,note\n,5,x\n,5,x,y\n5,\n"
    res = sol.load_rows(write(tmp_path, text), ["id", "amount"])
    assert res.rows == []
    assert res.errors == [
        {"line": 2, "reason": "missing_required"},
        {"line": 3, "reason": "too_many_fields"},
        {"line": 4, "reason": "too_few_fields"},
    ], "field count (step 6) is checked before required values (step 7)"


def test_footer_and_header_variants(sol, tmp_path):
    """Footers match case-insensitively on the whole first field; a re-header with extra spaces is still a header"""
    text = (
        "id,amount\n"
        "1,10\n"
        "total,10\n"
        "Exported 1 row\n"
        " id , amount \n"
        "totally_real,20\n"
        "GRAND TOTAL,30\n"
    )
    res = sol.load_rows(write(tmp_path, text), ["id"])
    assert [r["id"] for r in res.rows] == ["1", "totally_real", "GRAND TOTAL"], (
        "only a first field that is exactly TOTAL / Exported N row(s) is a footer"
    )
    assert res.errors == []


def test_missing_required_column_raises(sol, tmp_path):
    """A header without a required column raises SchemaError listing what's missing, in required order"""
    p = write(tmp_path, "# c\nannotator,amount_usd\nann_1,5\n")
    with pytest.raises(sol.SchemaError) as exc:
        sol.load_rows(p, ["task_id", "amount_usd", "annotator_id"])
    assert exc.value.missing == ["task_id", "annotator_id"]


def test_no_header_raises(sol, tmp_path):
    """A file with only comments and blank lines raises SchemaError with every required column"""
    p = write(tmp_path, "# nothing here\n\n#  still nothing\n")
    with pytest.raises(sol.SchemaError) as exc:
        sol.load_rows(p, ["id", "amount"])
    assert exc.value.missing == ["id", "amount"]
