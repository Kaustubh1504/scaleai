from collections import Counter
from pathlib import Path

from .pipeline import ingest
from .serialize import export_roster

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def build_report(data_dir=None):
    per_source, rejected, roster, duplicates = ingest(data_dir or DATA_DIR)
    skills = Counter(s for c in roster.values() for s in c.skills)
    return {
        "sources": per_source,
        "rejected": rejected,
        "roster": {
            email: {"name": c.name, "country": c.country, "hours": c.hours, "skills": c.skills, "sources": c.sources}
            for email, c in roster.items()
        },
        "duplicates": duplicates,
        "skill_counts": dict(sorted(skills.items())),
        "countries": dict(sorted(Counter(c.country for c in roster.values()).items())),
        "export": export_roster(roster),
    }
