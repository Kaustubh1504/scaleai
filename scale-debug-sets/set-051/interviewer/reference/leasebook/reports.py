from datetime import datetime
from pathlib import Path

from .ledger import Ledger
from .loader import load_events, load_tasks
from .models import DEAD

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CLOSE_OF_DAY = datetime(2026, 6, 1, 12, 0)


def _fmt(ts):
    return ts.strftime("%Y-%m-%d %H:%M")


def run(data_dir=None, close=CLOSE_OF_DAY):
    data_dir = Path(data_dir or DATA_DIR)
    ledger = Ledger(load_tasks(data_dir / "tasks.csv"))
    for event in load_events(data_dir / "events.csv"):
        ledger.handle(event)
    ledger.reap(close)
    return ledger


def worker_table(ledger):
    workers = sorted({w for _, w, _, _ in ledger.claims})
    return {
        w: {
            "claims": sum(1 for _, cw, _, tid in ledger.claims if cw == w and tid),
            "acks": ledger.acks[w],
            "lost": ledger.lost[w],
        }
        for w in workers
    }


def build_report(data_dir=None):
    ledger = run(data_dir)
    tasks = sorted(ledger.tasks.values(), key=lambda t: t.id)
    return {
        "claims": [[_fmt(at), w, q, tid] for at, w, q, tid in ledger.claims],
        "status": {t.id: t.status for t in tasks},
        "attempts": {t.id: t.attempts for t in tasks},
        "rejected": [[_fmt(at), action, w, tid] for at, action, w, tid in ledger.rejected],
        "workers": worker_table(ledger),
        "dead_letter": [t.id for t in tasks if t.status == DEAD],
        "extensions": {t.id: t.extensions for t in tasks if t.extensions},
    }
