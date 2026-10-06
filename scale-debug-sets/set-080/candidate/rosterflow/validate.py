from .models import Record
from .normalize import clean_email, parse_active, parse_hours, parse_skills, parse_updated, text

MAX_HOURS = 60


def check_row(raw, priority):
    """Return ("ok", Record) | ("inactive", None) | ("rejected", reason)."""
    f = raw.fields
    email = clean_email(f.get("email"))
    if not email:
        return "rejected", "missing email"
    local, at, domain = email.partition("@")
    if not local or not at or "." not in domain:
        return "rejected", "invalid email"
    updated = parse_updated(f.get("updated_at"))
    if updated is None:
        return "rejected", "unparseable date"
    hours = parse_hours(f.get("hours_per_week"))
    if hours is None or not 0 <= hours <= MAX_HOURS:
        return "rejected", "invalid hours"
    if not parse_active(f.get("active")):
        return "inactive", None
    record = Record(
        email=email,
        name=" ".join(text(f.get("name")).split()),
        country=text(f.get("country")).upper(),
        skills=parse_skills(f.get("skills")),
        hours=hours,
        updated_at=updated,
        source=raw.source,
        priority=priority,
    )
    return "ok", record
