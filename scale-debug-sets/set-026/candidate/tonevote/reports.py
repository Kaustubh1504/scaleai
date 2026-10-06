from collections import Counter, defaultdict
from pathlib import Path

from .agreement import agreement_table, votes_by_annotator
from .consensus import count_labels, resolve
from .loader import load_annotations, load_projects, load_teams

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def team_summary(roster, votes):
    members = defaultdict(list)
    for aid, team in roster.items():
        members[team].append(aid)
    return {
        team: {"members": sorted(ids), "votes": sum(votes[a] for a in ids)}
        for team, ids in sorted(members.items())
    }


def label_breakdown(results, projects):
    overall = Counter()
    by_project = {}
    for pid in sorted(projects):
        rows = [r for r in results.values() if r.project == pid]
        by_project[pid] = dict(sorted(count_labels(rows).items()))
        count_labels(rows, overall)
    return {"by_project": by_project, "overall": dict(sorted(overall.items()))}


def build_report(data_dir=None):
    data_dir = Path(data_dir or DATA_DIR)
    projects = load_projects(data_dir / "projects.json")
    annotations = load_annotations(data_dir / "batches", projects)
    results = resolve(annotations, projects)
    table = agreement_table(annotations, results)
    return {
        "tasks": {
            tid: {"project": r.project, "status": r.status, "label": r.label, "votes": r.votes}
            for tid, r in results.items()
        },
        "annotators": {
            aid: {
                "agreed_tasks": row.agreed_tasks,
                "agreement": round(row.rate, 3) if row.rate else None,
                "skips": row.skips,
            }
            for aid, row in table.items()
        },
        "labels": label_breakdown(results, projects),
        "teams": team_summary(load_teams(data_dir / "teams.csv"), votes_by_annotator(annotations)),
    }
