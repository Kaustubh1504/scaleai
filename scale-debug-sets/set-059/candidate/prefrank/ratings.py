from collections import defaultdict

K = 32
START = 1000.0


# VERIFIED
def expected(ra, rb):
    """Probability that the player rated ra beats the player rated rb."""
    return 1 / (1 + 10 ** ((rb - ra) / 400))


def elo(comparisons):
    ratings = defaultdict(lambda: START)
    for c in comparisons:
        a, b = c.pair
        score_a = 0.5 if c.winner is None else (1.0 if c.winner == a else 0.0)
        ea = expected(ratings[a], ratings[b])
        delta = K * (score_a - ea)
        ratings[a] += delta
        ratings[b] -= delta
    return {m: round(r, 1) for m, r in sorted(ratings.items())}


def win_rates(comparisons):
    stats = defaultdict(lambda: {"games": 0, "wins": 0, "ties": 0})
    for c in comparisons:
        for m in c.pair:
            stats[m]["games"] += 1
            if c.winner is None:
                stats[m]["ties"] += 1
            elif c.winner == m:
                stats[m]["wins"] += 1
    return {
        m: dict(s, win_rate=round((s["wins"] + 0.5 * s["ties"]) / s["games"], 3))
        for m, s in sorted(stats.items())
    }
