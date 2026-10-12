import json
from problem_api import RECORDS


def get_path(obj, path, default=None):
    if not path: return obj
    for key in path.split("."):
        if isinstance(obj, dict) and key in obj: obj = obj[key]
        elif isinstance(obj, list) and key.isdecimal() and int(key) < len(obj): obj = obj[int(key)]
        else: return default
    return obj


def clean(v):
    return v.strip() if isinstance(v, str) and (v := v.strip()) and v.lower() != "null" else None


def find(record, paths):
    return next((val for p in paths if (val := clean(get_path(record, p)))), None)


def to_profile(record):
    # ID (Required)
    pid = next((str(v) if type(v) is int else clean(v) for p in ["id", "annotator_id"] if (v := record.get(p)) is not None and (type(v) is int or clean(v) is not None)), None)
    if pid is None: raise ValueError("record has no id")

    # Name, Email, Country, City
    name = find(record, ["name", "profile.full_name"]) or f"{find(record, ['profile.first_name']) or ''} {find(record, ['profile.last_name']) or ''}".strip() or None
    email = (e := find(record, ["email", "contact.email"])) and e.lower()
    country = (c := find(record, ["country", "address.country", "addresses.0.country"])) and c.upper()
    city = find(record, ["city", "address.city", "addresses.0.city"])

    # Skills
    skills = next(([i for raw in val if (i := clean(raw))] for p in ["skills", "profile.skills"] if isinstance(val := get_path(record, p), list) or (isinstance(val, str) and (val := val.split(",")))), [])

    # Rating
    rating = next((float(v) if type(v) in (int, float) else float(c_val) for p in ["rating", "stats.rating"] if (v := get_path(record, p)) is not None and (type(v) in (int, float) or ((c_val := clean(v)) is not None and _is_float(c_val)))), None)

    # Active Status
    active = record.get("active")
    if isinstance(active, str): active = {"true": True, "false": False}.get(active.strip().lower())
    if not isinstance(active, bool):
        status = clean(record.get("status"))
        active = status is not None and status.lower() == "active"

    return {"id": pid, "name": name, "email": email, "country": country, "city": city, "skills": skills, "rating": rating, "active": active}


def _is_float(v):
    try: float(v); return True
    except ValueError: return False


if __name__ == "__main__":
    for rec in RECORDS:
        print(json.dumps(rec, indent=2))
        print(to_profile(rec))