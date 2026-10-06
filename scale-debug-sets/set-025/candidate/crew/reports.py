from pathlib import Path

from .allocator import allocate
from .loader import best_scores, load_contributors, load_projects

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def build_report(data_dir=DATA_DIR):
    data_dir = Path(data_dir)
    people = load_contributors(data_dir / "contributors.csv")
    scores = best_scores(data_dir / "assessments.csv")
    projects = load_projects(data_dir / "projects.csv")

    allocations, unfilled, remaining = allocate(projects, people, scores)
    available = [c for c in people if c.active and c.capacity > 0]
    used = {c.id: c.capacity - remaining[c.id] for c in available}
    return {
        "allocations": {pid: allocations[pid] for pid in sorted(allocations)},
        "unfilled": dict(sorted(unfilled.items())),
        "utilization": {c.id: round(used[c.id] / c.capacity, 2) for c in sorted(available, key=lambda c: c.id)},
        "idle": sorted(c.id for c in available if used[c.id] == 0),
    }
