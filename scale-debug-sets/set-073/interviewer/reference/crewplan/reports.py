from pathlib import Path

from .eligibility import current_certs
from .loader import load_completions, load_config, load_contributors, load_projects
from .models import CourseStats, Status
from .scheduler import staff

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def course_table(projects, certs):
    table = {}

    def stats(course):
        if course not in table:
            table[course] = CourseStats(course)
        return table[course]

    for cid, courses in certs.items():
        for course in courses:
            stats(course).holders.add(cid)
    for project in projects:
        for course in project.required_courses:
            entry = stats(course)
            if project.status is Status.OPEN:
                entry.demand += 1
    return {course: table[course] for course in sorted(table)}


def most_demanded(table):
    if not table:
        return None
    return min(table.values(), key=lambda s: (-s.demand, s.course_id)).course_id


def build_report(data_dir=None):
    data_dir = Path(data_dir or DATA_DIR)
    config = load_config(data_dir / "config.json")
    contributors = load_contributors(data_dir / "contributors.csv")
    projects = load_projects(data_dir / "projects.csv")
    certs = current_certs(load_completions(data_dir / "completions.csv"), config)

    assignments, open_seats = staff(projects, contributors, certs)
    table = course_table(projects, certs)
    return {
        "assignments": dict(sorted(assignments.items())),
        "open_seats": dict(sorted(open_seats.items())),
        "courses": {course: s.as_dict() for course, s in table.items()},
        "most_demanded": most_demanded(table),
    }
