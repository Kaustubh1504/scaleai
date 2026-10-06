from datetime import datetime

TS_FORMATS = ("%Y-%m-%d %H:%M", "%m/%d/%Y %H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d")
TRUTHY = {"true", "yes", "y", "1"}


def text(value):
    return str(value if value is not None else "").strip()


# VERIFIED
def clean_email(value):
    """Trim, lower-case and drop a leading 'mailto:'; local part and domain are otherwise kept as-is."""
    email = text(value).lower()
    if email.startswith("mailto:"):
        email = email[len("mailto:"):]
    return email


def parse_updated(value):
    raw = text(value)
    for fmt in TS_FORMATS:
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None


def parse_active(value):
    if value is None or text(value) == "":
        return True
    return bool(value)


def parse_skills(value):
    """'Python; SQL;' or ['python', 'sql'] -> ['python', 'sql'] (lower-case, blanks dropped)."""
    items = value if isinstance(value, list) else text(value).split(";")
    return [text(s).lower() for s in items]


def parse_hours(value):
    raw = text(value)
    try:
        return int(float(raw))
    except ValueError:
        return None
