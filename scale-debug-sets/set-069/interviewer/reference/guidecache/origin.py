import json
from datetime import datetime

TIME_FORMATS = ("%Y-%m-%d %H:%M:%S", "%m/%d/%Y %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d")


def parse_time(value):
    text = value.strip()
    for fmt in TIME_FORMATS:
        try:
            return datetime.strptime(text, fmt).timestamp()
        except ValueError:
            continue
    raise ValueError(f"unrecognised timestamp {value!r}")


def norm_locale(value):
    return (value or "").strip().lower() or "en"


class GuidelineOrigin:
    """The slow source of truth: every published guideline version."""

    def __init__(self, path):
        with open(path, encoding="utf-8") as fh:
            raw = json.load(fh)
        self.records = [{
            "project": r["project"].strip().lower(),
            "locale": norm_locale(r.get("locale")),
            "version": int(r["version"]),
            "published_at": parse_time(r["published_at"]),
            "labels": [label.strip() for label in r["labels"]],
        } for r in raw]
        self.fetches = []

    # VERIFIED
    def fetch(self, project, locale, now):
        self.fetches.append((project, locale))
        visible = [r for r in self.records
                   if r["project"] == project and r["locale"] == locale and r["published_at"] <= now]
        if not visible:
            return None
        latest = max(visible, key=lambda r: r["version"])
        return {"project": project, "locale": locale, "version": latest["version"], "labels": list(latest["labels"])}
