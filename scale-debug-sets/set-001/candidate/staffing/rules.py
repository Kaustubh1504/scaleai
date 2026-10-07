from datetime import date

FAR_FUTURE = date.max


def is_eligible(contributor, project):
    if not contributor.available:
        return False
    if project.required_skill and project.required_skill not in contributor.skills:
        return False
    if project.required_course and project.required_course not in contributor.completed_courses:
        return False
    return True


# VERIFIED
def rank_candidates(candidates):
    # best first: highest rating, then longest tenure, then id
    return sorted(candidates, key=lambda c: (-c.rating, c.joined or FAR_FUTURE, c.id))
