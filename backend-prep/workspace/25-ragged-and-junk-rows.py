"""25. Ragged rows, repeated headers and footers

Template: imports, constants, exceptions and signatures are here.
Fill in every `raise NotImplementedError` (add your own helpers as needed)."""

from __future__ import annotations
import csv
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
import io

FOOTER = re.compile(r"(total|exported \d+ rows?)", re.IGNORECASE)


class SchemaError(Exception):
    def __init__(self, missing: list[str]):
        super().__init__(f"missing required columns: {missing}")
        self.missing = missing


@dataclass
class Result:
    rows: list[dict[str, str]] = field(default_factory=list)
    errors: list[dict] = field(default_factory=list)

footer_regex = re.compile(r"TOTAL|Exported \d+ row(s)?", re.IGNORECASE)

def load_rows(path: str | os.PathLike, required: list[str]) -> Result:
    data = Path(path).read_bytes()
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise CsvFormatError(f"{path}: not valid UTF-8 ({exc.reason} at byte {exc.start})") from None

    reader = csv.reader(io.StringIO(text, newline=""), delimiter=",")
    errors = []
    cdata = []
    prev_end = 0
    for row in reader:
        start = prev_end + 1              # physical line where this record starts
        prev_end = reader.line_num
        srow = [r.strip() for r in row]
        if not any(srow) or srow[0].startswith("#"):
            continue
        cdata.append((start, srow))

            
    if not cdata:
        raise SchemaError(list(required))
    
    header = cdata[0][1]
    missing = [r for r in required if r not in header]
    if missing:
        raise SchemaError(missing)
    
    res = Result()
    for line, row in cdata:
        if row == header or footer_regex.fullmatch(row[0]):
            continue   
            
        if len(row)<len(header):
            res.errors.append({"line": line, "reason": "too_few_fields"})
        
        elif len(row)>len(header):
            res.errors.append({"line": line, "reason": "too_many_fields"})

        else:
            rec = dict(zip(header, row))
            if any(rec[r] == "" for r in required):
                res.errors.append({"line": line, "reason": "missing_required"})
            else:
                res.rows.append(rec)
        
    return res


if __name__ == "__main__":
    from problem_api import PAYOUTS, REQUIRED

    res = load_rows(PAYOUTS, REQUIRED)
    print(len(res.rows), "rows:", [r["annotator_id"] for r in res.rows])
    for err in res.errors:
        print("  line", err["line"], err["reason"])
