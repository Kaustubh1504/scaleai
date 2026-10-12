"""25. Ragged rows, repeated headers and footers

Template: imports, constants, exceptions and signatures are here.
Fill in every `raise NotImplementedError` (add your own helpers as needed)."""

from __future__ import annotations
import csv
import os
import re
from dataclasses import dataclass, field

FOOTER = re.compile(r"(total|exported \d+ rows?)", re.IGNORECASE)


class SchemaError(Exception):
    def __init__(self, missing: list[str]):
        super().__init__(f"missing required columns: {missing}")
        self.missing = missing


@dataclass
class Result:
    rows: list[dict[str, str]] = field(default_factory=list)
    errors: list[dict] = field(default_factory=list)


def load_rows(path: str | os.PathLike, required: list[str]) -> Result:
    raise NotImplementedError


if __name__ == "__main__":
    from problem_api import PAYOUTS, REQUIRED

    res = load_rows(PAYOUTS, REQUIRED)
    print(len(res.rows), "rows:", [r["annotator_id"] for r in res.rows])
    for err in res.errors:
        print("  line", err["line"], err["reason"])
