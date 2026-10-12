"""24. Read an ugly CSV export

Template: imports, constants, exceptions and signatures are here.
Fill in every `raise NotImplementedError` (add your own helpers as needed)."""

from __future__ import annotations
import csv
import io
import os
import re
from pathlib import Path

CANDIDATES = (",", ";", "\t")


class CsvFormatError(Exception):
    pass


def normalize_header(name: str) -> str:
    raise NotImplementedError


def read_csv(path: str | os.PathLike) -> list[dict[str, str]]:
    raise NotImplementedError


if __name__ == "__main__":
    from problem_api import ALL_FILES

    for p in ALL_FILES:
        try:
            rows = read_csv(p)
            print(f"{p.name}: {len(rows)} rows, columns {list(rows[0]) if rows else []}")
        except CsvFormatError as exc:
            print(f"{p.name}: CsvFormatError: {exc}")
