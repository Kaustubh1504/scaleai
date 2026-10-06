from .rules import is_eligible, rank_key


def project_order(projects):
    # higher priority number staffs first
    return sorted(projects, key=lambda p: (-p.priority, p.id))


def staff(projects, contributors):
    assignments = {}
    for project in project_order(projects):
        picked = []
        if project.seats > 0:
            pool = sorted((c for c in contributors.values() if is_eligible(c, project)), key=rank_key)
            for contributor in pool[:project.seats]:
                contributor.hours_left -= project.hours_per_seat
                contributor.projects.append(project.id)
                picked.append(contributor.id)
        assignments[project.id] = picked
    return assignments
