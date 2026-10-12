import pytest

from problem_api import ANNOTATORS_TSV, CONTACTS_BOM, DUP_HEADERS, LATIN1_EXPORT, SINGLE_COLUMN, VENDOR_SEMICOLON


def write(tmp_path, text, name="upload.csv"):
    p = tmp_path / name
    p.write_bytes(text.encode("utf-8"))
    return p


def test_bom_and_header_normalization(sol):
    """BOM file: headers are normalized and the first key has no \\ufeff"""
    rows = sol.read_csv(CONTACTS_BOM)
    assert rows, "expected rows from the contacts file"
    keys = list(rows[0])
    assert keys == ["email_address", "full_name", "sign_up_date_utc", "notes"], (
        f"got keys {keys!r}; a leading '\\ufeff' means the BOM was not stripped (use utf-8-sig)"
    )


def test_quoted_comma_and_newline(sol):
    """Quoted cells keep their commas and embedded newlines"""
    rows = sol.read_csv(CONTACTS_BOM)
    assert rows[0]["notes"] == "Prefers email, not phone", "a quoted comma must not split the field"
    assert rows[1]["notes"] == "Line one\nline two", "a quoted newline is part of the value, not a new row"


def test_blank_lines_skipped_values_stripped(sol):
    """Blank and whitespace-only lines are skipped; values are stripped"""
    rows = sol.read_csv(CONTACTS_BOM)
    assert [r["email_address"] for r in rows] == ["ana@example.com", "bo@example.com", "cy@example.com"], (
        "expected exactly 3 contacts: empty lines and '   ,  ,  ,  ' are not records"
    )
    assert rows[0]["full_name"] == "Ana Lima", "values must be stripped (' Ana Lima ' -> 'Ana Lima')"
    assert rows[2]["notes"] == "", "an empty trailing cell is ''"


def test_semicolon_delimiter(sol):
    """A ';'-delimited file is detected; decimal commas and a quoted ';' stay intact"""
    rows = sol.read_csv(VENDOR_SEMICOLON)
    assert list(rows[0]) == ["task_id", "annotator", "hours", "rate_eur"], f"wrong columns: {list(rows[0])}"
    assert [r["hours"] for r in rows] == ["7,5", "3", "4,25"], "'7,5' is one value in a ';' file"
    assert rows[1]["annotator"] == "Élodie Martin", "UTF-8 text must decode correctly"
    assert rows[2]["annotator"] == "Anna; Maria Rossi", "a quoted ';' must not split the field"


def test_tab_delimiter(sol):
    """A tab-delimited file is detected"""
    rows = sol.read_csv(ANNOTATORS_TSV)
    assert rows == [
        {"annotator_id": "ann_17", "language_s": "en, de", "qa_score": "97.5"},
        {"annotator_id": "ann_42", "language_s": "ja", "qa_score": "88"},
    ]


def test_single_column_falls_back_to_comma(sol):
    """A one-column file (nothing to sniff) still parses"""
    assert sol.read_csv(SINGLE_COLUMN) == [{"email": "a@x.com"}, {"email": "b@x.com"}]


def test_normalize_header(sol):
    """normalize_header strips, lowercases and collapses non-alphanumeric runs to '_'"""
    cases = {
        " Email Address ": "email_address",
        "Sign-up Date (UTC)": "sign_up_date_utc",
        "QA Score %": "qa_score",
        "__user--ID__": "user_id",
        "already_ok": "already_ok",
        "Rate (EUR)": "rate_eur",
    }
    for raw, expected in cases.items():
        assert sol.normalize_header(raw) == expected, f"normalize_header({raw!r})"


def test_duplicate_and_empty_headers(sol):
    """Duplicate names get _2, _3; empty names become column_<n>"""
    rows = sol.read_csv(DUP_HEADERS)
    assert rows == [{"score": "0.9", "score_2": "0.8", "score_3": "0.7", "notes": "ok", "column_5": "x", "column_6": "y"}], (
        "headers 'Score,score, SCORE ,Notes,,#' should become score, score_2, score_3, notes, column_5, column_6"
    )


def test_non_utf8_raises(sol):
    """A Latin-1 file raises CsvFormatError instead of returning mojibake"""
    with pytest.raises(sol.CsvFormatError):
        sol.read_csv(LATIN1_EXPORT)


def test_short_rows_padded_trailing_delimiters_ok(sol, tmp_path):
    """Short records are padded with ''; blank extra fields (trailing commas) are ignored"""
    p = write(tmp_path, "id,name,email\n1,Ana\n2,Bo,bo@x.com,,\n")
    assert sol.read_csv(p) == [
        {"id": "1", "name": "Ana", "email": ""},
        {"id": "2", "name": "Bo", "email": "bo@x.com"},
    ]


def test_extra_non_blank_field_raises(sol, tmp_path):
    """A non-blank field beyond the header raises CsvFormatError"""
    p = write(tmp_path, "id,name\n1,Ana\n2,Bo,surprise\n")
    with pytest.raises(sol.CsvFormatError):
        sol.read_csv(p)


def test_empty_and_header_only(sol, tmp_path):
    """An empty file, a blank-lines-only file and a header-only file all return []"""
    assert sol.read_csv(write(tmp_path, "", "empty.csv")) == []
    assert sol.read_csv(write(tmp_path, "\n\n  \n", "blank.csv")) == []
    assert sol.read_csv(write(tmp_path, "id,name\n\n", "header.csv")) == []
