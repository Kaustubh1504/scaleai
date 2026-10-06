import json


def parse_embeddings(text, expected, dims):
    """Vectors from an embeddings response body, in input order.

    Raises json.JSONDecodeError for a body that is not JSON, and ValueError for JSON
    that does not hold exactly `expected` vectors of length `dims`.
    """
    body = json.loads(text)
    items = body.get("data") if isinstance(body, dict) else None
    if not isinstance(items, list) or len(items) != expected:
        raise ValueError(f"expected {expected} embeddings, got {len(items) if isinstance(items, list) else 'none'}")
    by_index = {}
    for item in items:
        vector = item.get("embedding")
        if not isinstance(vector, list) or len(vector) != dims:
            raise ValueError("embedding length does not match dimensions")
        by_index[item.get("index")] = [float(x) for x in vector]
    if sorted(by_index) != list(range(expected)):
        raise ValueError("embedding indexes do not cover the inputs")
    return [by_index[i] for i in range(expected)]
