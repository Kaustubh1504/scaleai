import csv
import json
from datetime import datetime

from .models import Contributor, CourseResult, Project

DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%d %b %Y")
DEFAULT_RATING = 3.0
TRUE_WORDS = {"y", "yes", "true", "1"}


def clean(value):
    return str(value if value is not None else "").strip()


def parse_date(value):
    text = clean(value)
    if not text:
        return None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"unrecognised date: {value!r}")


def _number(value):
    text = clean(value)
    return float(text) if text else None


def load_contributors(path):
    contributors = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            cid = clean(row["id"]).upper()
            rating = _number(row["rating"])
            contributors[cid] = Contributor(
                cid=cid,
                name=clean(row["name"]),
                locale=clean(row["locale"]).lower(),
                weekly_hours=_number(row["weekly_hours"]) or 0.0,
                rating=rating or DEFAULT_RATING,
                active=clean(row["active"]).lower() in TRUE_WORDS,
                joined=parse_date(row["joined"]),
            )
    return contributors


def load_courses(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return [
            CourseResult(
                contributor_id=clean(row["contributor_id"]).upper(),
                course=clean(row["course"]).lower(),
                result=clean(row["result"]).lower(),
                taken_on=parse_date(row["taken_on"]),
            )
            for row in csv.DictReader(fh)
        ]


def load_projects(path):
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    return [
        Project(
            id=clean(item["id"]).upper(),
            name=clean(item["name"]),
            priority=int(item["priority"]),
            seats=int(item["seats"]),
            hours_per_seat=float(item["hours_per_seat"]),
            locale=clean(item.get("locale")).lower(),
            courses=tuple(clean(c).lower() for c in item.get("courses", []) if clean(c)),
        )
        for item in raw
    ]
