import csv
from datetime import date, datetime
from pathlib import Path

from .models import Contributor, Project

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%d %b %Y")
TRUTHY = {"y", "yes", "true", "1"}


def _clean(value):
    return (value or "").strip()


def _split(value):
    return [part.strip() for part in _clean(value).split(";") if part.strip()]


# VERIFIED
def parse_date(value):
    text = _clean(value)
    if not text:
        return None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"unrecognised date: {value!r}")


def load_contributors(path=None):
    path = path or DATA_DIR / "contributors.csv"
    contributors = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            contributors.append(Contributor(
                id=_clean(row["contributor_id"]).upper(),
                name=_clean(row["name"]),
                skills={s.lower() for s in _split(row["skills"])},
                completed_courses=set(_split(row["completed_courses"])),
                rating=float(_clean(row["rating"]) or 0),
                joined=parse_date(row["joined"]),
                available=_clean(row["available"]).lower() in TRUTHY,
            ))
    return contributors


def load_projects(path=None):
    path = path or DATA_DIR / "projects.csv"
    projects = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            projects.append(Project(
                id=_clean(row["project_id"]).upper(),
                name=_clean(row["name"]),
                priority=int(_clean(row["priority"])),
                headcount=int(_clean(row["headcount"]) or 0),
                required_skill=_clean(row["required_skill"]).lower(),
                required_course=_clean(row["required_course"]).upper() or None,
            ))
    return projects
