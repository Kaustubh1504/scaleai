"""24. Read an ugly CSV export

Template: imports, constants, exceptions and signatures are here.
Fill in every `raise NotImplementedError` (add your own helpers as needed)."""

from __future__ import annotations
import csv
import io
import os
import re
from pathlib import Path
import pandas as pd

CANDIDATES = (",", ";", "\t")


class CsvFormatError(Exception):
    pass


def normalize_header(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(name).strip().lower()).strip("_")

def detect_delimiter(text):
    try:
        return csv.Sniffer().sniff(text[:4096],delimiters="".join(CANDIDATES)).delimiter
    except:
        pass
    first = next((line for line in text.splitlines() if line.strip()),"")
    
    best = ","
    best_count = 0
    
    for d in CANDIDATES:
        count = first.count(d)
        if count > best_count:
            best = d
            best_count = count
        
    return best
    

def read_csv(path: str | os.PathLike) -> list[dict[str, str]]:
    data = Path(path).read_bytes()
    
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise CsvFormatError(f"{path}: not valid UTF-8 ({exc.reason} at byte {exc.start})") from None
    
    try:
        df = pd.read_csv(
            path,
            sep=None,
            engine="python",
            encoding="utf-8-sig",
            skip_blank_lines=True,
            dtype=str,  
            keep_default_na=False
        )
    except Exception as exc:
        raise CsvFormatError(f"{path}: parsing failed ({exc})") from exc
        
    
    raw_cols = df.columns.tolist()
    new_cols = []
    seen = {}
    
    for i, col in enumerate(raw_cols, start=1):
        if str(col).startswith("Unnamed:"):
            name = f"column_{i}"
        else:
            name = normalize_header(col) or f"column_{i}"
            
        seen[name] = seen.get(name, 0) + 1
        new_cols.append(name if seen[name] == 1 else f"{name}_{seen[name]}")

    df.columns = new_cols

    df = df.apply(lambda col: col.str.strip())

    return df.to_dict(orient="records")
        

if __name__ == "__main__":
    from problem_api import ALL_FILES

    for p in ALL_FILES:
        try:
            rows = read_csv(p)
            print(f"{p.name}: {len(rows)} rows, columns {list(rows[0]) if rows else []}")
        except CsvFormatError as exc:
            print(f"{p.name}: CsvFormatError: {exc}")
