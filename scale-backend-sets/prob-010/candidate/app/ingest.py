"""Parse uploaded document files (JSONL or CSV) and validate each row."""

from __future__ import annotations

import csv
import io
import json
import re
from dataclasses import dataclass, field
from typing import Iterator

FIELDS = ("doc_id", "title", "text")
# Document ids end up in URLs; keep them boring.
DOC_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
MAX_TEXT_CHARS = 20_000

# A parsed record, or None plus a reason when the row's structure is broken.
Row = tuple[dict | None, str | None]


class IngestError(ValueError):
    """The file as a whole is unusable (HTTP 400)."""


@dataclass
class ParsedFile:
    total_rows: int = 0
    documents: list[tuple[int, dict]] = field(default_factory=list)  # (row number, {doc_id, title, text})
    errors: list[dict] = field(default_factory=list)  # {"row", "error"}


def _decode(raw: bytes) -> str:
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise IngestError("file is not valid UTF-8") from exc
    if not text.strip():
        raise IngestError("file is empty")
    return text


def _jsonl_rows(text: str) -> Iterator[Row]:
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            yield None, "line is not valid JSON"
            continue
        yield (record, None) if isinstance(record, dict) else (None, "line is not a JSON object")


def _csv_rows(text: str) -> Iterator[Row]:
    reader = csv.reader(io.StringIO(text, newline=""))
    header = next((row for row in reader if row), None)
    names = [name.strip() for name in header or []]
    missing = [f for f in FIELDS if f not in names]
    if missing:
        raise IngestError(f"header is missing required columns: {', '.join(missing)}")
    for values in reader:
        if not values:  # blank line
            continue
        if len(values) != len(names):
            yield None, f"expected {len(names)} values, got {len(values)}"
        else:
            yield dict(zip(names, values)), None


PARSERS = {".jsonl": _jsonl_rows, ".csv": _csv_rows}


def _problem(doc: dict, seen_ids: set[str]) -> str | None:
    """The first rule the document breaks, or None if it is valid."""
    if not doc["doc_id"]:
        return "doc_id is required"
    if not DOC_ID_RE.match(doc["doc_id"]):
        return "doc_id may only contain letters, digits, '_' and '-' (max 64)"
    if doc["doc_id"] in seen_ids:
        return f"duplicate doc_id {doc['doc_id']!r} in this file"
    if not doc["title"]:
        return "title is required"
    if not doc["text"]:
        return "text is required"
    if len(doc["text"]) > MAX_TEXT_CHARS:
        return f"text is longer than {MAX_TEXT_CHARS} characters"
    return None


def parse_upload(suffix: str, raw: bytes) -> ParsedFile:
    """Parse a whole file. ``suffix`` is a key of PARSERS. Row numbers are 1-based data rows."""
    result = ParsedFile()
    seen_ids: set[str] = set()
    for row_number, (record, structural_error) in enumerate(PARSERS[suffix](_decode(raw)), start=1):
        result.total_rows = row_number
        if record is None:
            result.errors.append({"row": row_number, "error": structural_error})
            continue
        # Non-string values (JSONL) count as missing.
        doc = {f: record[f].strip() if isinstance(record.get(f), str) else "" for f in FIELDS}
        problem = _problem(doc, seen_ids)
        if problem:
            result.errors.append({"row": row_number, "error": problem})
        else:
            seen_ids.add(doc["doc_id"])
            result.documents.append((row_number, doc))
    return result
