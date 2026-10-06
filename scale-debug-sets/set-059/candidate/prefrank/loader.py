import csv
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

TRUE_WORDS = {"true", "yes", "y", "1"}
TIME_FORMATS = ("%Y-%m-%d %H:%M", "%m/%d/%Y %H:%M", "%Y-%m-%dT%H:%M:%S")


@dataclass(frozen=True)
class Comparison:
    prompt_id: str
    rater: str
    pair: tuple       # the two model ids, sorted
    winner: str | None  # model id, or None for a tie
    created_at: datetime
    row: int


def parse_flag(value):
    if isinstance(value, str):
        return value.strip().lower() in TRUE_WORDS
    return bool(value)


def parse_time(text):
    text = text.strip()
    for fmt in TIME_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError(f"unrecognised time {text!r}")


def load_raters(path):
    """Ids of qualified raters."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return {r["rater_id"].strip().lower() for r in raw if parse_flag(r.get("qualified", False))}


def read_comparisons(path, qualified):
    out = []
    with open(path, newline="", encoding="utf-8") as fh:
        for n, row in enumerate(csv.DictReader(fh), start=2):
            rater = row["rater"].strip()
            choice = row["winner"].strip().lower()
            if rater not in qualified or choice not in ("a", "b", "tie"):
                continue
            model_a, model_b = row["model_a"].strip().lower(), row["model_b"].strip().lower()
            swapped = bool(row["swapped"].strip())
            if swapped:
                choice = {"a": "b", "b": "a"}.get(choice, choice)
            winner = {"a": model_a, "b": model_b}.get(choice)
            out.append(Comparison(row["prompt_id"].strip().lower(), rater, tuple(sorted((model_a, model_b))),
                                  winner, parse_time(row["created_at"]), n))
    return out
