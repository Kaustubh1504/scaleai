def region_ok(contributor, project):
    return contributor.region == project.region or "any"


def is_eligible(contributor, project, scores):
    if not contributor.active or contributor.capacity <= 0:
        return False
    if not region_ok(contributor, project):
        return False
    best = scores.get(contributor.id, {}).get(project.skill)
    return best is not None and best >= project.min_score
