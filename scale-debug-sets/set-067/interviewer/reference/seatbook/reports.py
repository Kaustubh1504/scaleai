from collections import Counter
from pathlib import Path

from .booking import Venue
from .loader import load_requests, load_seats

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PRICES = {"premium": 120, "standard": 80, "balcony": 55}


def run(data_dir=None):
    data_dir = Path(data_dir or DATA_DIR)
    venue = Venue(load_seats(data_dir / "seats.csv"))
    requests = load_requests(data_dir / "requests.csv")
    for req in requests:
        venue.handle(req)
    return venue, requests


def build_report(data_dir=None):
    venue, requests = run(data_dir)
    sold = [s for s in venue.seats if s.status == "sold"]
    by_section = Counter(s.section for s in sold)
    return {
        "held_seats": venue.held_seats,
        "statuses": venue.statuses,
        "actions": {r.request_id: r.action for r in requests},
        "summary": {
            "sold": len(sold),
            "revenue": sum(PRICES[s.tier] for s in sold),
            "sold_by_section": dict(sorted(by_section.items())),
            "ignored": sorted(rid for rid, st in venue.statuses.items() if st == "ignored"),
        },
    }
