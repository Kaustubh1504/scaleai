from collections import Counter
from pathlib import Path

from .loader import load_contributors, load_rates, load_tasks
from .pricing import task_pay, to_local

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def build_report(data_dir=DATA_DIR):
    data_dir = Path(data_dir)
    rates = load_rates(data_dir / "rates.json")
    people = load_contributors(data_dir / "contributors.csv")
    tasks = load_tasks(data_dir / "tasks.csv")

    accepted = [t for t in tasks if t.status == "accepted" and t.contributor_id in people]
    pay = {t.task_id: task_pay(t, rates) for t in accepted}

    earned = {cid: 0 for cid in people}
    counts = Counter()
    for task in accepted:
        earned[task.contributor_id] += pay[task.task_id]
        counts.update(task.contributor_id)

    contributors = {}
    for cid in sorted(people):
        person = people[cid]
        total = earned[cid]
        if total >= person.min_payout:
            payout, held = to_local(total, person.currency, rates), 0
        else:
            payout, held = 0, total
        contributors[cid] = {"earned_usd_cents": total, "currency": person.currency,
                             "payout": payout, "held_usd_cents": held}

    top = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:3]
    return {
        "task_pay": dict(sorted(pay.items())),
        "contributors": contributors,
        "top_contributors": [[cid, n] for cid, n in top],
    }
