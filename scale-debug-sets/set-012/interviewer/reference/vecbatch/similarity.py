import math
from itertools import combinations


def cosine(u, v):
    dot = sum(a * b for a, b in zip(u, v))
    norm = math.sqrt(sum(a * a for a in u)) * math.sqrt(sum(b * b for b in v))
    return dot / norm if norm else 0.0


def near_duplicates(vectors, threshold):
    """[doc_a, doc_b, similarity] for every pair at or above threshold, most similar first."""
    pairs = []
    for a, b in combinations(sorted(vectors), 2):
        sim = round(cosine(vectors[a], vectors[b]), 3)
        if sim >= threshold:
            pairs.append([a, b, sim])
    return sorted(pairs, key=lambda p: (-p[2], p[0], p[1]))
