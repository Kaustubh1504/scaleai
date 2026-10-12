"""24. Read an ugly CSV export: reference solution."""

import csv
import io
import os
import re
from pathlib import Path


class CsvFormatError(Exception):
    pass


def normalize_header(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")


def read_csv(path: str | os.PathLike) -> list[dict[str, str]]:
    try:
        text = Path(path).read_bytes().decode("utf-8-sig")
    except UnicodeDecodeError:
        raise CsvFormatError(f"{path}: not valid UTF-8") from None
    first = next((line for line in text.splitlines() if line.strip()), "")
    delim = max(",;\t", key=first.count)  # max keeps the first on ties, so "," wins ties/zeros
    header, rows = None, []
    for record in csv.reader(io.StringIO(text, newline=""), delimiter=delim):
        values = [v.strip() for v in record]
        if not any(values):
            continue
        if header is None:
            header, seen = [], {}
            for i, col in enumerate(values, start=1):
                name = normalize_header(col) or f"column_{i}"
                seen[name] = seen.get(name, 0) + 1
                header.append(name if seen[name] == 1 else f"{name}_{seen[name]}")
            continue
        if any(values[len(header):]):
            raise CsvFormatError(f"{path}: record has more fields than the header")
        values += [""] * (len(header) - len(values))
        rows.append(dict(zip(header, values)))
    return rows


if __name__ == "__main__":
    from problem_api import ALL_FILES

    for p in ALL_FILES:
        try:
            print(p.name, read_csv(p)[:1])
        except CsvFormatError as exc:
            print(p.name, "CsvFormatError:", exc)
