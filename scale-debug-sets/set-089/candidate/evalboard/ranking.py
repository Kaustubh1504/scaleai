def rank_board(rows, last_seen):
    """Highest composite first; on a tie the team that finished submitting earlier wins."""
    ordered = sorted(rows, key=lambda r: (-r["composite"], last_seen[r["team"]], r["team"]))
    for position, row in enumerate(ordered, start=1):
        row["rank"] = position
    return ordered
