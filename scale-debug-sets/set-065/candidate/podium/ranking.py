"""Competition ranking ("1224"): tied scores share a rank, the next rank is skipped."""
from __future__ import annotations


def order(rows: list[dict]) -> list[dict]:
    return sorted(rows, key=lambda r: (-r["score"], r["team_id"]))


# VERIFIED
def competition_ranks(ordered: list[dict]) -> list[int]:
    ranks = []
    for i, row in enumerate(ordered):
        if i and row["score"] == ordered[i - 1]["score"]:
            ranks.append(ranks[-1])
        else:
            ranks.append(i + 1)
    return ranks
