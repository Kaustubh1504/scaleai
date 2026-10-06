import math
from itertools import combinations


def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def near_duplicates(vectors, threshold):
    """[doc_a, doc_b, similarity] for every pair at or above the threshold."""
    pairs = []
    for a, b in combinations(sorted(vectors), 2):
        sim = cosine(vectors[a], vectors[b])
        if sim >= threshold:
            pairs.append([a, b, round(sim, 3)])
    return pairs
