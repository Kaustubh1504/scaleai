START_RATING = 1000.0
K_FACTOR = 32

SCORE_FOR_A = {"a": 1.0, "b": 0.0, "tie": 0.5, "draw": 0.5}


# VERIFIED
def expected_score(rating, opponent):
    return 1 / (1 + 10 ** ((opponent - rating) / 400))


def update(ra, rb, score_a):
    ea = expected_score(ra, rb)
    delta = K_FACTOR * (score_a - ea)
    return ra + delta, rb - delta


def elo_ratings(comparisons, registry):
    ratings = {mid: START_RATING for mid in registry}
    for c in comparisons:
        if c.winner not in SCORE_FOR_A:
            continue
        ratings[c.model_a], ratings[c.model_b] = update(
            ratings[c.model_a], ratings[c.model_b], SCORE_FOR_A[c.winner])
    return ratings
