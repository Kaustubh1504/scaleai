from datetime import date


# VERIFIED
def latest_results(results):
    """(contributor, course) -> the most recent result; on the same day the later row wins."""
    latest = {}
    for res in results:
        key = (res.contributor_id, res.course)
        if key not in latest or res.taken_on >= latest[key].taken_on:
            latest[key] = res
    return latest


def attach_courses(contributors, results):
    for (cid, course), res in latest_results(results).items():
        if cid in contributors:
            contributors[cid].courses[course] = res.result


def missing_course(contributor, required):
    """The first required course the contributor has not passed, or None."""
    for course in required:
        if contributor.courses.get(course) != "pass":
            return course
    return None


def is_eligible(contributor, project):
    if not contributor.active:
        return False
    if project.locale and contributor.locale != project.locale:
        return False
    if missing_course(contributor, project.courses) is not None:
        return False
    return contributor.hours_left >= project.hours_per_seat


# VERIFIED
def rank_key(contributor):
    return (-contributor.rating, contributor.joined or date.max, contributor.id)
