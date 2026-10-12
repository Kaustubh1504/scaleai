"""Sample files for problem 24. Paths are absolute (the judge runs in a temp dir)."""

from __future__ import annotations

from pathlib import Path

DATA = Path(__file__).resolve().parent / "data"

CONTACTS_BOM = DATA / "contacts_bom.csv"          # UTF-8 BOM, CRLF, quoted comma + newline, blank lines
VENDOR_SEMICOLON = DATA / "vendor_semicolon.csv"  # ';' delimiter, decimal commas
ANNOTATORS_TSV = DATA / "annotators.tsv"          # tab delimiter
DUP_HEADERS = DATA / "dup_headers.csv"            # repeated / empty header names
LATIN1_EXPORT = DATA / "latin1_export.csv"        # not UTF-8 at all
SINGLE_COLUMN = DATA / "single_column.csv"        # no delimiter anywhere

ALL_FILES = [CONTACTS_BOM, VENDOR_SEMICOLON, ANNOTATORS_TSV, DUP_HEADERS, LATIN1_EXPORT, SINGLE_COLUMN]
