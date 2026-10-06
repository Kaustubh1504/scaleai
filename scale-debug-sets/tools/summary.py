"""Print the batch summary table (set, domain, length, difficulty, status, bug types).

    python tools/summary.py               # every set that has bugs defined
    python tools/summary.py 1 5           # sets 1..5
"""
from __future__ import annotations

import sys

from common import load_manifest


def main(argv: list[str]) -> int:
    lo, hi = (int(argv[0]), int(argv[1])) if len(argv) == 2 else (1, 10_000)
    rows = [s for s in load_manifest()["sets"] if lo <= int(s["id"].split("-")[1]) <= hi and s.get("bugs")]
    print("| Set | Domain | Length | Difficulty | Format | Status | Bugs (type @ file) |")
    print("|---|---|---|---|---|---|---|")
    for s in rows:
        bugs = "; ".join(f"{b['id']} {b['type']} @ {b['file'].split('/')[-1]}"
                         + (" (masked)" if b.get("masked_by") or b.get("visible_only_in") else "")
                         for b in s["bugs"])
        print(f"| {s['id']} | {s['domain']} | {s['length']} | {s['difficulty']} | {s.get('format', 'multi')} | {s['status']} | {bugs} |")
    sets = load_manifest()["sets"]
    done = sum(1 for s in sets if s["status"] == "verified")
    print(f"\n{done}/{len(sets)} verified; next pending: "
          f"{next((s['id'] for s in sets if s['status'] == 'pending'), 'none')}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
