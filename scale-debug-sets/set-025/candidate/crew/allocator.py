from .rules import is_eligible


def project_order(projects):
    return sorted(projects, key=lambda p: (-p.priority, p.id))


# VERIFIED
def candidate_order(candidates, project, scores, remaining):
    return sorted(candidates, key=lambda c: (-scores[c.id][project.skill], -remaining[c.id], c.id))


def allocate(projects, people, scores):
    remaining = {c.id: c.capacity for c in people}
    allocations, unfilled = {}, {}
    for project in project_order(projects):
        needed = project.hours_needed
        plan = {}
        eligible = [c for c in people if is_eligible(c, project, scores)]
        for cand in candidate_order(eligible, project, scores, remaining):
            if needed == 0:
                break
            if remaining[cand.id] == 0:
                break
            hours = min(remaining[cand.id], needed)
            plan[cand.id] = hours
            remaining[cand.id] -= hours
            needed -= hours
        allocations[project.id] = plan
        if needed:
            unfilled[project.id] = needed
    return allocations, unfilled, remaining
