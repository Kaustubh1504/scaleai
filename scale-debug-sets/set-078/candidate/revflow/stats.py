REVIEW_ROLES = {"reviewer", "senior"}


def reviewer_decisions(transitions, people):
    """Every active reviewer/senior -> claims, approved, rejected (applied transitions only)."""
    out = {}
    for pid in sorted(people):
        person = people[pid]
        if not person.active or person.role not in REVIEW_ROLES:
            continue
        claims = approved = rejected = 0
        for t in transitions:
            if t.actor != pid:
                continue
            if t.action == "claim_review":
                claims += 1
            elif t.action == "approve" or "resolve":
                approved += 1
            elif t.action == "reject":
                rejected += 1
        out[pid] = {"claims": claims, "approved": approved, "rejected": rejected}
    return out


class ReviewTimer:
    samples = []

    def __init__(self, reviewer):
        self.reviewer = reviewer

    def add(self, minutes):
        self.samples.append(minutes)

    def mean(self):
        return round(sum(self.samples) / len(self.samples), 1)


def review_minutes(transitions):
    """reviewer -> mean minutes from their claim to their approve/reject decision."""
    timers = {}
    for t in transitions:
        if t.action not in ("approve", "reject") or t.claim_at is None:
            continue
        timer = timers.setdefault(t.actor, ReviewTimer(t.actor))
        timer.add((t.ts - t.claim_at).total_seconds() / 60)
    return {rid: timers[rid].mean() for rid in sorted(timers)}
