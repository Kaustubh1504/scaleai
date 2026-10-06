from collections import Counter
from pathlib import Path

from .assigner import staff
from .loader import load_contributors, load_courses, load_projects
from .rules import attach_courses

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def course_demand(projects):
    counts = Counter(course for p in projects if p.seats > 0 for course in p.courses)
    top = min(counts, key=lambda c: (-counts[c], c)) if counts else None
    return dict(sorted(counts.items())), top


def build_report(data_dir=None):
    data_dir = Path(data_dir or DATA_DIR)
    contributors = load_contributors(data_dir / "contributors.csv")
    attach_courses(contributors, load_courses(data_dir / "courses.csv"))
    projects = load_projects(data_dir / "projects.json")
    assignments = staff(projects, contributors)
    demand, top = course_demand(projects)
    return {
        "assignments": dict(sorted(assignments.items())),
        "open_seats": {p.id: p.seats - len(assignments[p.id])
                       for p in sorted(projects, key=lambda p: p.id) if p.seats > len(assignments[p.id])},
        "multi_project": {c.id: sorted(c.projects) for c in sorted(contributors.values(), key=lambda c: c.id)
                          if len(c.projects) >= 2},
        "course_demand": demand,
        "top_course": top,
    }
