from collections import defaultdict
from pathlib import Path

from .assigner import staff
from .loader import load_contributors, load_projects
from .rules import is_available

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def skill_gaps(projects, unfilled):
    gaps = defaultdict(int)
    for project in projects:
        gaps[project.skill] += unfilled[project.id]
    return dict(sorted(gaps.items()))


def build_report(data_dir=None):
    data_dir = Path(data_dir or DATA_DIR)
    contributors = load_contributors(data_dir / "contributors.csv")
    projects = load_projects(data_dir / "projects.csv")
    assignments = staff(projects, contributors)
    unfilled = {p.id: p.seats - len(assignments.get(p.id, [])) for p in projects}
    return {
        "assignments": assignments,
        "unfilled": {pid: unfilled[pid] for pid in assignments},
        "skill_gaps": skill_gaps(projects, unfilled),
        "utilisation": {
            c.id: round(c.hours_used / c.weekly_hours, 2)
            for c in sorted(contributors, key=lambda c: c.id)
            if is_available(c) and c.weekly_hours
        },
    }
