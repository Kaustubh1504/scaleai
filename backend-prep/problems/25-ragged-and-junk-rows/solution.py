"""25. Ragged rows, repeated headers and footers: reference solution."""

import csv
import os
import re
from dataclasses import dataclass


class SchemaError(Exception):
    def __init__(self, missing: list[str]):
        super().__init__(f"missing required columns: {missing}")
        self.missing = missing


@dataclass
class Result:
    rows: list[dict[str, str]]
    errors: list[dict]


def load_rows(path: str | os.PathLike, required: list[str]) -> Result:
    rows, errors, header, end = [], [], None, 0
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        for record in reader:
            line, end = end + 1, reader.line_num  # starts right after the previous record
            values = [v.strip() for v in record]
            if not any(values) or values[0].startswith("#"):
                continue
            if header is None:
                header = values
                if missing := [c for c in required if c not in header]:
                    raise SchemaError(missing)
            elif values == header or re.fullmatch(r"total|exported \d+ rows?", values[0], re.I):
                continue
            elif len(values) > len(header):
                errors.append({"line": line, "reason": "too_many_fields"})
            elif len(values) < len(header):
                errors.append({"line": line, "reason": "too_few_fields"})
            elif not all(values[header.index(c)] for c in required):
                errors.append({"line": line, "reason": "missing_required"})
            else:
                rows.append(dict(zip(header, values)))
    if header is None:
        raise SchemaError(list(required))
    return Result(rows, errors)


if __name__ == "__main__":
    from problem_api import PAYOUTS, REQUIRED

    res = load_rows(PAYOUTS, REQUIRED)
    print([r["annotator_id"] for r in res.rows], res.errors)
