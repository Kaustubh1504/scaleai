"""27. Flatten nested JSON to CSV and back: reference solution."""

import csv
import io
import re
from typing import Any


def flatten(obj: dict, sep: str = ".") -> dict[str, Any]:
    if not isinstance(obj, dict):
        raise TypeError(f"flatten expects a dict, got {type(obj).__name__}")
    out = {}

    def walk(value, prefix):
        if isinstance(value, dict):
            for key, child in value.items():
                if not key or sep in key:
                    raise ValueError(f"key {key!r} is empty or contains {sep!r}")
                walk(child, f"{prefix}{sep}{key}" if prefix else key)
        elif isinstance(value, list):
            for i, child in enumerate(value):
                walk(child, f"{prefix}{sep}{i}")
        else:
            out[prefix] = value

    walk(obj, "")
    return out


def to_csv_text(records: list[dict], sep: str = ".") -> str:
    if not records:
        return ""
    flat = [flatten(r, sep) for r in records]
    columns = list(dict.fromkeys(key for row in flat for key in row))
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(columns)
    for row in flat:
        values = [row.get(c) for c in columns]  # csv.writer writes None as ""
        writer.writerow([str(v).lower() if isinstance(v, bool) else v for v in values])
    return buf.getvalue()


def unflatten(flat: dict[str, Any], sep: str = ".") -> dict:
    tree = {}
    for key, value in flat.items():
        parts = key.split(sep)
        if "" in parts:
            raise ValueError(f"empty path segment in {key!r}")
        node = tree
        for part in parts[:-1]:
            node = node.setdefault(part, {})
            if not isinstance(node, dict):
                raise ValueError(f"{key!r} goes through a key that is already a value")
        if parts[-1] in node:
            raise ValueError(f"{key!r} is both a value and a prefix of another key")
        node[parts[-1]] = value

    def build(node):
        if not isinstance(node, dict):
            return node
        node = {k: build(v) for k, v in node.items()}
        is_index = [bool(re.fullmatch(r"0|[1-9][0-9]*", k)) for k in node]
        if not any(is_index):
            return node
        if not all(is_index) or sorted(map(int, node)) != list(range(len(node))):
            raise ValueError(f"bad list indexes: {sorted(node)}")
        return [node[str(i)] for i in range(len(node))]

    return {k: build(v) for k, v in tree.items()}


if __name__ == "__main__":
    from problem_api import load_tasks

    tasks = load_tasks()
    print(flatten(tasks[0]))
    print(to_csv_text(tasks))
