from collections import Counter


def win_rates(comparisons):
    """games, and (wins + half of ties) / games per model."""
    games, wins, ties = Counter(), Counter(), Counter()
    for comp in comparisons:
        games.update(comp.models)
        if comp.winner is None:
            ties.update(comp.models)
        else:
            wins[comp.winner] += 1
    rates = {m: round((wins[m] + 0.5 * ties[m]) / games[m], 3) for m in sorted(games)}
    return dict(sorted(games.items())), rates
