from .rules import can_take, skill_level


# VERIFIED
def project_order(projects):
    # higher priority number is more important
    return sorted((p for p in projects if p.status == "open"), key=lambda p: (-p.priority, p.id))


def staff(projects, contributors):
    assignments = {}
    for project in project_order(projects):
        picked = []
        while len(picked) < project.seats:
            pool = [c for c in contributors if c.id not in picked and can_take(c, project)]
            if not pool:
                break
            best = min(pool, key=lambda c: (-skill_level(c, project.skill), -c.remaining, c.id))
            best.hours_used += project.hours_per_seat
            picked.append(best.id)
        assignments[project.id] = picked
    return assignments
