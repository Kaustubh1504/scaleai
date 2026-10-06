import csv
from dataclasses import dataclass

DEFAULT_HOURS = 20


def clean(value):
    return str(value if value is not None else "").strip()


@dataclass
class Contributor:
    id: str
    region: str
    capacity: int
    active: bool


@dataclass
class Project:
    id: str
    skill: str
    min_score: int
    hours_needed: int
    priority: int
    region: str


def _rows(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def load_contributors(path):
    people = []
    for row in _rows(path):
        hours = clean(row["weekly_hours"])
        people.append(Contributor(
            id=clean(row["contributor_id"]).upper(),
            region=clean(row["region"]).lower(),
            capacity=int(hours) if hours else DEFAULT_HOURS,
            active=clean(row["active"]).lower() in {"y", "yes", "true", "1"},
        ))
    return people


def best_scores(path):
    """{contributor_id: {skill: best finished score}}."""
    attempts = {}
    for row in _rows(path):
        score = clean(row["score"])
        if not score:
            continue
        cid = clean(row["contributor_id"]).upper()
        attempts.setdefault(cid, {}).setdefault(clean(row["skill"]).lower(), []).append(score)
    return {
        cid: {skill: max(int(s) for s in scores) for skill, scores in skills.items()}
        for cid, skills in attempts.items()
    }


def load_projects(path):
    projects = []
    for row in _rows(path):
        projects.append(Project(
            id=clean(row["project_id"]).upper(),
            skill=clean(row["skill"]).lower(),
            min_score=int(clean(row["min_score"])),
            hours_needed=int(clean(row["hours_needed"]) or 0),
            priority=int(clean(row["priority"])),
            region=clean(row["region"]).lower() or "any",
        ))
    return projects
