from .assigner import assign
from .loader import DATA_DIR, load_contributors, load_projects


def open_seats(projects, assignments):
    seats = {}
    for project in projects:
        missing = project.headcount - len(assignments.get(project.id, []))
        if missing > 0:
            seats[project.id] = missing
    return dict(sorted(seats.items()))


def bench(contributors, assignments):
    staffed = {cid for ids in assignments.values() for cid in ids}
    return sorted(c.id for c in contributors if c.available and c.id not in staffed)


def build_report(data_dir=None):
    data_dir = data_dir or DATA_DIR
    contributors = load_contributors(data_dir / "contributors.csv")
    projects = load_projects(data_dir / "projects.csv")
    assignments = assign(contributors, projects)
    return {
        "assignments": dict(sorted(assignments.items())),
        "open_seats": open_seats(projects, assignments),
        "bench": bench(contributors, assignments),
    }
