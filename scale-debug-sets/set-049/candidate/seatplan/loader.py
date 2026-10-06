import csv
from dataclasses import dataclass


@dataclass
class Contributor:
    id: str
    region: str
    skills: list
    weekly_hours: int
    status: str
    hours_used: int = 0

    @property
    def remaining(self):
        return self.weekly_hours - self.hours_used


@dataclass(frozen=True)
class Project:
    id: str
    priority: int
    region: str
    skill: str
    min_level: int
    seats: int
    hours_per_seat: int
    status: str


def clean(value):
    return str(value if value is not None else "").strip()


def parse_skills(text):
    skills = []
    for part in clean(text).split(";"):
        if not clean(part):
            continue
        name, _, level = part.partition(":")
        skills.append((clean(name).lower(), int(level) if clean(level) else 1))
    return skills


def _rows(path):
    with open(path, newline="", encoding="utf-8") as fh:
        yield from csv.DictReader(fh)


def load_contributors(path):
    return [
        Contributor(
            id=clean(r["contributor_id"]).upper(),
            region=clean(r["region"]).lower(),
            skills=parse_skills(r["skills"]),
            weekly_hours=int(clean(r["weekly_hours"]) or 0),
            status=clean(r["status"]).lower(),
        )
        for r in _rows(path)
    ]


def load_projects(path):
    return [
        Project(
            id=clean(r["project_id"]).upper(),
            priority=int(clean(r["priority"])),
            region=clean(r["region"]).lower(),
            skill=clean(r["skill"]).lower(),
            min_level=int(clean(r["min_level"])),
            seats=int(clean(r["seats"])),
            hours_per_seat=int(clean(r["hours_per_seat"])),
            status=clean(r["status"]).lower(),
        )
        for r in _rows(path)
    ]
