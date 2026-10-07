import csv
import json
from dataclasses import dataclass
from datetime import date, datetime

DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%b %d %Y")
TRUTHY = {"yes", "y", "true", "1"}


@dataclass(frozen=True)
class Config:
    model: str
    max_concurrency: int
    max_retries: int
    backoff_seconds: float
    baseline_page_size: int
    default_max_tokens: int
    new_since: date


@dataclass(frozen=True)
class Prompt:
    id: str
    suite: str
    priority: int
    review: bool
    added: date
    text: str
    expected: str
    max_tokens: int


def parse_date(value):
    text = value.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"unrecognised date {value!r}")


def load_config(path):
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    return Config(
        model=raw["model"].strip(),
        max_concurrency=int(raw.get("max_concurrency", 4)),
        max_retries=int(raw.get("max_retries", 2)),
        backoff_seconds=float(raw.get("backoff_seconds", 1.0)),
        baseline_page_size=int(raw.get("baseline_page_size", 50)),
        default_max_tokens=int(raw.get("default_max_tokens", 64)),
        new_since=parse_date(raw["new_since"]),
    )


def load_suites(path, default_max_tokens):
    """suite name -> max_tokens budget for its prompts."""
    suites = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            budget = row["max_tokens"].strip()
            suites[row["suite"].strip().lower()] = int(budget) if budget else default_max_tokens
    return suites


def load_prompts(path, suites):
    prompts = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            text = " ".join(row["prompt"].split())
            if not text:
                continue
            suite = row["suite"].strip().lower()
            prompts.append(Prompt(
                id=row["prompt_id"].strip().lower(),
                suite=suite,
                priority=int(row["priority"]),
                review=row["review"].strip().lower() in TRUTHY,
                added=parse_date(row["added"]),
                text=text,
                expected=row["expected"],
                max_tokens=suites[suite],
            ))
    return sorted(prompts, key=lambda p: (p.priority, p.id))
