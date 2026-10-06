import csv
import json
from dataclasses import dataclass
from datetime import datetime

TIME_FORMATS = ("%Y-%m-%d %H:%M", "%m/%d/%Y %H:%M", "%Y-%m-%dT%H:%M:%S")


@dataclass(frozen=True)
class Pair:
    pair_id: str
    prompt_id: str
    model_a: str
    model_b: str
    gold: str  # "A", "B" or "" for regular pairs


@dataclass(frozen=True)
class Judgement:
    judgement_id: str
    pair_id: str
    labeler_id: str
    left_model: str
    rating: int
    submitted_at: datetime


def clean(value):
    return (value or "").strip()


def norm_id(value):
    return clean(value).lower()


def norm_model(value):
    return clean(value).lower()


def parse_when(value):
    text = clean(value)
    for fmt in TIME_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError(f"unrecognised timestamp {value!r}")


def parse_active(value):
    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "y", "1"}
    return bool(value)


def load_labelers(path):
    with open(path, encoding="utf-8") as fh:
        return {norm_id(row["id"]): parse_active(row.get("active", True)) for row in json.load(fh)}


def load_pairs(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return {
            clean(row["pair_id"]).upper(): Pair(
                clean(row["pair_id"]).upper(), clean(row["prompt_id"]),
                norm_model(row["model_a"]), norm_model(row["model_b"]), clean(row["gold"]).upper(),
            )
            for row in csv.DictReader(fh)
        }


def load_judgements(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return [
            Judgement(
                clean(row["judgement_id"]), clean(row["pair_id"]).upper(), norm_id(row["labeler_id"]),
                clean(row["left_model"]), int(row["rating"]), parse_when(row["submitted_at"]),
            )
            for row in csv.DictReader(fh)
        ]


def latest_only(judgements):
    """One judgement per (pair, labeler): the latest; on equal times the later row wins."""
    keep = {}
    for j in judgements:
        key = (j.pair_id, j.labeler_id)
        if key not in keep or j.submitted_at >= keep[key].submitted_at:
            keep[key] = j
    return list(keep.values())
