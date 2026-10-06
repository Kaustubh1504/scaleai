from .rules import is_eligible, rank_candidates


def project_order(projects):
    # most important first, ties by project id
    return sorted(projects, key=lambda p: (p.priority, p.id))


def assign(contributors, projects):
    assignments = {}
    taken = set()
    for project in project_order(projects):
        if project.headcount <= 0:
            assignments[project.id] = []
            continue
        pool = [c for c in contributors if c.id not in taken and is_eligible(c, project)]
        chosen = rank_candidates(pool)[: project.headcount]
        taken.update(c.id for c in chosen)
        assignments[project.id] = [c.id for c in chosen]
    return assignments
