ELIGIBLE_STATUSES = ("active", "trial")


def is_available(contributor):
    return contributor.status in ELIGIBLE_STATUSES


def skill_level(contributor, skill):
    for name, level in contributor.skills:
        if name == skill:
            return level
    return 0


def can_take(contributor, project):
    return (
        is_available(contributor)
        and project.region in ("any", contributor.region)
        and skill_level(contributor, project.skill) >= project.min_level
        and contributor.remaining >= project.hours_per_seat
    )
