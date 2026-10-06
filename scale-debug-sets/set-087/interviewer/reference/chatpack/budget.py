TURN_OVERHEAD = 4


# VERIFIED
def count_tokens(text):
    return len(text.split()) + TURN_OVERHEAD


def pair_cost(pair):
    user, assistant = pair
    return count_tokens(user.content) + count_tokens(assistant.content)


def fit_budget(system, pairs, budget):
    """Drop the oldest pairs until the example fits.

    Returns (kept pairs, number dropped, token total of what is kept).
    The newest pair is never dropped, so the total can still exceed the budget.
    """
    costs = [pair_cost(p) for p in pairs]
    total = (count_tokens(system.content) if system else 0) + sum(costs)
    start = 0
    while total > budget and start < len(pairs) - 1:
        total -= costs[start]
        start += 1
    return pairs[start:], start, total
