# 36. Stream JSONL (read huge files, append safely, resume)
# Standalone: copy this file as-is. Deps: stdlib

import json
import os


def iter_jsonl(path, errors=None):
    """Yield (line_no, obj) one line at a time (constant memory). Bad lines -> errors, skipped."""
    with open(path, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                yield n, json.loads(line)
            except ValueError:
                if errors is not None:
                    errors.append({"line": n, "error": "invalid_json"})


def append_jsonl(path, records) -> int:
    """Append records, one JSON object per line, and fsync. Returns how many were written."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    n = 0
    with open(path, "a", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n += 1
        f.flush()
        os.fsync(f.fileno())
    return n


def count_complete_lines(path) -> int:
    """Lines that end in a newline: where to resume after a crash (a torn last line doesn't count)."""
    if not os.path.exists(path):
        return 0
    with open(path, "rb") as f:
        return sum(chunk.count(b"\n") for chunk in iter(lambda: f.read(1 << 20), b""))
