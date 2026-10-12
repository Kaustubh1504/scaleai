"""31. End-to-end cleaning pipeline: reference solution."""

import csv
import io
import json
import os
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

UTC = timezone.utc
COLUMNS = ("submission_id", "task_id", "annotator_id", "label", "submitted_at", "payout")
REASONS = {"label": "bad_label", "submitted_at": "bad_timestamp", "payout": "bad_payout"}


@dataclass
class Summary:
    rows_read: int = 0
    invalid_rows: int = 0
    duplicates_dropped: int = 0
    conflicts: int = 0
    superseded_rows: int = 0
    unknown_annotator_rows: int = 0
    clean_rows: int = 0


def _normalize(raw: dict[str, str]) -> tuple[dict, list[tuple[str, str]]]:
    rec, errors = {}, []
    for field in COLUMNS:
        value = raw[field]
        if not value:
            errors.append((field, "missing"))
            continue
        try:
            if field == "label":
                if value.lower() not in {"cat", "dog", "other"}:
                    raise ValueError
                rec[field] = value.lower()
            elif field == "submitted_at":
                if value.isdigit():
                    dt = datetime.fromtimestamp(int(value), UTC)
                else:
                    dt = datetime.fromisoformat(value.upper())
                dt = dt.replace(tzinfo=dt.tzinfo or UTC).astimezone(UTC)
                rec[field] = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            elif field == "payout":
                dollars = value.removeprefix("$").replace(",", "")
                if not re.fullmatch(r"\d+(\.\d{1,2})?", dollars):
                    raise ValueError
                rec["payout_cents"] = int(Decimal(dollars) * 100)
            else:
                rec[field] = value.upper()
        except ValueError:
            errors.append((field, REASONS[field]))
    return rec, errors


def run_pipeline(csv_path: str | os.PathLike, annotators_path: str | os.PathLike,
                 out_dir: str | os.PathLike) -> Summary:
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        header = [h.strip().lower() for h in next(reader, [])]
        if missing := [c for c in COLUMNS if c not in header]:
            raise ValueError(f"missing required columns {missing}")
        rows = []
        for cells in reader:
            cells = [c.strip() for c in cells] + [""] * len(header)  # pad short rows
            if any(cells):
                rows.append((reader.line_num, {c: cells[header.index(c)] for c in COLUMNS}))
    annotators = json.loads(Path(annotators_path).read_text("utf-8"))
    known = {str(a["annotator_id"]).strip().upper() for a in annotators}

    summary = Summary(rows_read=len(rows))
    errors, versions = [], {}
    for line, raw in rows:
        rec, field_errors = _normalize(raw)
        if field_errors:
            summary.invalid_rows += 1
            errors += [(line, field, reason) for field, reason in field_errors]
            continue
        group = versions.setdefault(rec["submission_id"], [])
        if any(rec == seen for _, seen in group):
            summary.duplicates_dropped += 1
        else:
            group.append((line, rec))

    clean = []
    for group in versions.values():
        # normalized "...Z" strings sort chronologically; ties go to the later line
        line, rec = max(group, key=lambda v: (v[1]["submitted_at"], v[0]))
        if len(group) > 1:
            summary.conflicts += 1
            summary.superseded_rows += len(group) - 1
            errors += [(ln, "submission_id", "superseded") for ln, _ in group if ln != line]
        if rec["annotator_id"] in known:
            clean.append(rec)
        else:
            summary.unknown_annotator_rows += 1
            errors.append((line, "annotator_id", "unknown_annotator"))
    summary.clean_rows = len(clean)

    errors.sort(key=lambda e: (e[0], COLUMNS.index(e[1])))
    clean.sort(key=lambda r: r["submission_id"])
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\n").writerows([("line", "field", "reason"), *errors])
    files = {
        "clean.jsonl": "".join(json.dumps(r) + "\n" for r in clean),
        "errors.csv": buf.getvalue(),
        "summary.json": json.dumps(asdict(summary), indent=2) + "\n",
    }
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    tmp = {name: out / f".{name}.tmp" for name in files}
    try:
        for name, text in files.items():
            tmp[name].write_text(text, encoding="utf-8", newline="")
        for name in files:
            os.replace(tmp[name], out / name)
    except BaseException:
        for path in tmp.values():
            path.unlink(missing_ok=True)
        raise
    return summary


if __name__ == "__main__":
    import tempfile

    from problem_api import ANNOTATORS_JSON, SUBMISSIONS_CSV

    with tempfile.TemporaryDirectory() as d:
        print(run_pipeline(SUBMISSIONS_CSV, ANNOTATORS_JSON, d))
        print((Path(d) / "errors.csv").read_text())
