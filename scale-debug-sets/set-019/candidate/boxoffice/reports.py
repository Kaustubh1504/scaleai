from collections import defaultdict
from pathlib import Path

from .booking import replay
from .loader import load_events, load_seats

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def build_report(data_dir=None):
    data_dir = Path(data_dir or DATA_DIR)
    seats = load_seats(data_dir / "seats.csv")
    office = replay(seats, load_events(data_dir / "events.csv"))
    by_customer = defaultdict(list)
    for seat_id, customer in office.sold.items():
        by_customer[customer].append(seat_id)
    revenue = sum(seats[s].price for s in office.sold)
    return {
        "sold": dict(sorted(office.sold.items())),
        "by_customer": {c: sorted(s) for c, s in sorted(by_customer.items())},
        "rejections": dict(sorted(office.rejections.items())),
        "revenue": round(revenue, 2),
        "occupancy_pct": round(100 * len(office.sold) / len(seats), 1),
    }
