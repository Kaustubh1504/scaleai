import csv
import json
from dataclasses import dataclass

from .parsing import normalised_score


@dataclass(frozen=True)
class Sample:
    sample_id: str
    model: str
    category: str


@dataclass(frozen=True)
class Judgment:
    judgment_id: str
    sample_id: str
    judge: str
    score: float


def _clean(value):
    return str(value if value is not None else "").strip()


def load_weights(path):
    with open(path, encoding="utf-8") as fh:
        rows = json.load(fh)
    return {_clean(r["category"]).lower(): float(_clean(r["weight"])) for r in rows}


def load_samples(path, weights):
    samples = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            category = _clean(row["category"]).lower()
            if category not in weights:
                continue
            sid = _clean(row["sample_id"]).lower()
            samples[sid] = Sample(sid, _clean(row["model"]).lower(), category)
    return samples


def load_judgments(path, samples):
    """Return (judgments with a readable score, ids of judgments that could not be read)."""
    judgments, failures = [], []
    with open(path, encoding="utf-8") as fh:
        for n, line in enumerate(fh, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            sid = _clean(row.get("sample")).lower()
            if sid not in samples:
                continue
            score = normalised_score(_clean(row.get("output")))
            if score is None:
                failures.append(_clean(row.get("id")).lower())
                continue
            judgments.append(Judgment(_clean(row.get("id")).lower(), sid, _clean(row.get("judge")).lower(), score))
    return judgments, failures
