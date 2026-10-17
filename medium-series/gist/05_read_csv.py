# 05. Read a messy CSV by header
# Standalone: copy this file as-is. Deps: stdlib + fastapi

import csv
import io
from pathlib import Path

from fastapi import HTTPException


def read_csv(path: Path, required: list[str]) -> tuple[list[str], list[tuple[int, list[str]]]]:
    """(header, [(row_no, values)]); row_no counts records from 1, header excluded.
    404 missing file, 422 not UTF-8 / empty / missing required header."""
    if not path.is_file():
        raise HTTPException(404, f"{path.name} not found")
    try:
        text = path.read_bytes().decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(422, f"{path.name} is not valid UTF-8") from None
    records = [[v.strip() for v in row] for row in csv.reader(io.StringIO(text, newline=""))]
    records = [r for r in records if any(r)]
    if not records:
        raise HTTPException(422, f"{path.name} is empty")
    header = records[0]
    missing = [c for c in required if c not in header]
    if missing:
        raise HTTPException(422, f"{path.name} missing columns: {', '.join(missing)}")
    return header, list(enumerate(records[1:], 1))
