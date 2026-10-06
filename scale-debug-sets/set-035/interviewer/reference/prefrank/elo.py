START = 1000.0
K = 32


# VERIFIED
def expected_score(rating, opponent):
    return 1 / (1 + 10 ** ((opponent - rating) / 400))


def elo_ratings(comparisons):
    """Sequential Elo over comparisons ordered by round (file order within a round)."""
    ratings = {}
    for comp in sorted(comparisons, key=lambda c: c.round):
        a, b = comp.model_a, comp.model_b
        ra, rb = ratings.get(a, START), ratings.get(b, START)
        score_a = 0.5 if comp.winner is None else (1.0 if comp.winner == a else 0.0)
        ea = expected_score(ra, rb)
        ratings[a] = ra + K * (score_a - ea)
        ratings[b] = rb + K * ((1 - score_a) - (1 - ea))
    return ratings
