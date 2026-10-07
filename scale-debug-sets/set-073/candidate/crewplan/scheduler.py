from .eligibility import is_eligible


def project_order(projects):
    # higher priority number = more important
    return sorted(projects, key=lambda p: (-p.priority, p.id))


# VERIFIED
def rank_candidates(pool, hours_left):
    return sorted(pool, key=lambda c: (-c.rating, -hours_left[c.id], c.id))


def staff(projects, contributors, certs):
    hours_left = {cid: c.weekly_hours for cid, c in contributors.items()}
    assignments, open_seats = {}, {}
    for project in project_order(projects):
        team = []
        assignments[project.id] = team
        if project.status == "paused":
            continue
        for _ in range(project.seats):
            pool = [c for c in contributors.values()
                    if c.id not in team and is_eligible(c, project, certs, hours_left)]
            if not pool:
                break
            pick = rank_candidates(pool, hours_left)[0]
            team.append(pick.id)
            hours_left[pick.id] -= project.hours_per_seat
        if len(team) < project.seats:
            open_seats[project.id] = project.seats - len(team)
    return assignments, open_seats
