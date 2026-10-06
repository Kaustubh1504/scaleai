from collections import defaultdict


# VERIFIED
def is_current(completed_on, as_of, valid_days):
    return 0 <= (as_of - completed_on).days <= valid_days


def current_certs(completions, config):
    """contributor id -> set of course ids they hold a current certification for."""
    certs = defaultdict(set)
    for cid, course, completed_on in completions:
        if is_current(completed_on, config["as_of"], config["valid_days"]):
            certs[cid].add(course)
    return certs


def is_eligible(contributor, project, certs, hours_left):
    if hours_left[contributor.id] < project.hours_per_seat:
        return False
    held = certs.get(contributor.id, set())
    return all(course in held for course in project.required_courses)
