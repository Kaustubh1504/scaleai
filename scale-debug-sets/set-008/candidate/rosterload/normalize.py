import copy
from datetime import datetime

from .schema import DEFAULTS, REQUIRED, MissingField, RowError, norm_country

DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%Y-%m-%dT%H:%M:%S")


def clean(value):
    return "" if value is None else str(value).strip()


# VERIFIED
def parse_date(value):
    text = clean(value)
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            pass
    raise RowError(f"bad date {value!r}")


def parse_rate(value):
    text = clean(value).lstrip("$")
    if text.endswith("/day"):
        rate = float(text[: -len("/day")]) // 8
    else:
        rate = float(text)
    if rate < 0:
        raise RowError(f"negative rate {value!r}")
    return round(rate, 2)


def parse_skills(value):
    return sorted({s.strip().lower() for s in clean(value).split(";") if s.strip()})


def valid_email(email):
    if email.count("@") != 1 or " " in email:
        return False
    local, domain = email.split("@")
    return bool(local) and "." in domain


def build_record(row, vendor, order):
    for field in REQUIRED:
        if not clean(row.get(field)):
            raise MissingField(field)
    email = clean(row["email"]).lower()
    if not valid_email(email):
        raise RowError(f"bad email {email!r}")

    record = dict(DEFAULTS)
    record["email"] = email
    record["vendor"] = vendor
    record["order"] = order
    record["updated_at"] = parse_date(row.get("updated_at"))
    record["sources"] = [f"{vendor}:{clean(row.get('source_ref'))}"]
    record["skills"] = parse_skills(row.get("skills"))
    record["country"] = norm_country(row.get("country"))

    name = clean(row.get("name"))
    if not name:
        name = email.split("@")[0]
        record["notes"].append("name_from_email")
    record["name"] = name

    if clean(row.get("hourly_rate")):
        record["hourly_rate"] = parse_rate(row["hourly_rate"])
    else:
        record["notes"].append("rate_missing")
    return record
