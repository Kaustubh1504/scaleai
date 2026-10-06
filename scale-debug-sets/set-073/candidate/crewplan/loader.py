import csv
import json
from datetime import date, datetime

from .models import Contributor, Project, Status

DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%b %d %Y")


def clean(value):
    return str(value if value is not None else "").strip()


def norm_id(value):
    return clean(value).upper()


def split_list(value):
    return tuple(norm_id(part) for part in clean(value).split(";") if clean(part))


def parse_date(value):
    text = clean(value)
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    raise ValueError(f"unrecognised date: {value!r}")


def _rows(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def load_config(path):
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    return {"as_of": date.fromisoformat(raw["as_of"]), "valid_days": int(raw["valid_days"])}


def load_contributors(path):
    out = {}
    for row in _rows(path):
        cid = norm_id(row["contributor_id"])
        out[cid] = Contributor(
            id=cid,
            name=clean(row["name"]),
            weekly_hours=int(clean(row["weekly_hours"]) or 0),
            rating=float(clean(row["rating"]) or 0),
        )
    return out


def load_projects(path):
    out = []
    for row in _rows(path):
        out.append(Project(
            id=norm_id(row["project_id"]),
            priority=int(clean(row["priority"])),
            status=Status(clean(row["status"]).lower()),
            seats=int(clean(row["seats"]) or 0),
            hours_per_seat=int(clean(row["hours_per_seat"])),
            required_courses=split_list(row["required_courses"]),
        ))
    return out


def load_completions(path):
    """[(contributor_id, course_id, completed_on)]"""
    return [
        (norm_id(row["contributor_id"]), norm_id(row["course_id"]), parse_date(row["completed_on"]))
        for row in _rows(path)
    ]
