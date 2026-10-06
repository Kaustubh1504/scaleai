from .models import Contributor


def pick_winner(group):
    """Latest updated_at wins; on a tie the most trusted source (priority 1) wins."""
    return max(group, key=lambda r: (r.updated_at, -r.priority))


def merge(records):
    """email -> Contributor, one per email."""
    groups = {}
    for record in records:
        groups.setdefault(record.email, []).append(record)
    merged = {}
    for email in sorted(groups):
        group = groups[email]
        winner = pick_winner(group)
        merged[email] = Contributor(
            email=email,
            name=winner.name,
            country=winner.country,
            hours=winner.hours,
            updated_at=winner.updated_at,
            skills=sorted({s for r in group for s in r.skills}),
            sources=sorted({r.source for r in group}),
        )
    return merged, sum(1 for g in groups.values() if len(g) > 1)
