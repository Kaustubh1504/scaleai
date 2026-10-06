from .models import ModelStats


def win_table(comparisons, registry):
    """Games, wins and ties for every registered model (both_bad counts as a game, no points)."""
    table = {mid: ModelStats(mid) for mid in registry}
    for c in comparisons:
        a, b = table[c.model_a], table[c.model_b]
        a.games += 1
        b.games += 1
        if c.winner == "a":
            a.wins += 1
        elif c.winner == "b":
            b.wins += 1
        elif c.winner == "tie" or c.winner == "draw":
            a.ties += 1
            b.ties += 1
    return table
