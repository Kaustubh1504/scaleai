import csv
import json
from datetime import datetime

from .models import Submission, Team

TIME_FORMATS = ("%Y-%m-%d %H:%M", "%m/%d/%Y %H:%M", "%Y-%m-%dT%H:%M:%S")


def clean(value):
    return str(value if value is not None else "").strip()


def norm_team(value):
    return clean(value).upper()


def parse_flag(value):
    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "1"}
    return bool(value)


def parse_time(value):
    text = clean(value)
    for fmt in TIME_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError(f"unrecognised time: {value!r}")


def load_teams(path):
    with open(path, encoding="utf-8") as fh:
        rows = json.load(fh)["teams"]
    teams = {}
    for row in rows:
        team = Team(norm_team(row["team_id"]), clean(row["name"]), parse_flag(row.get("disqualified", False)))
        teams[team.team_id] = team
    return teams


def load_submissions(path):
    subs = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            status = clean(row["status"]).lower() or "accepted"
            subs.append(Submission(
                submission_id=clean(row["submission_id"]),
                team_id=norm_team(row["team_id"]),
                submitted_at=parse_time(row["submitted_at"]),
                correct=int(clean(row["correct"])),
                total=int(clean(row["total"])),
                accepted=status == "accepted",
            ))
    return subs
