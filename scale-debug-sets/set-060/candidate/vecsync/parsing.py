class ResponseError(ValueError):
    """The embeddings response could not be used."""


class DimensionMismatch(ResponseError):
    """A vector came back with an unexpected length."""


def parse_embeddings(body, count, dimensions):
    """Vectors in input order from an embeddings response body."""
    if not isinstance(body, dict) or not isinstance(body.get("data"), list):
        raise ResponseError("missing data list")
    items = sorted(body["data"], key=lambda d: d["index"])
    if [d["index"] for d in items] != list(range(count)):
        raise ResponseError("indexes do not cover the input")
    vectors = [d["embedding"] for d in items]
    for i, vec in enumerate(vectors):
        if len(vec) != dimensions:
            raise DimensionMismatch(f"input {i}: got {len(vec)} dims, want {dimensions}")
    return vectors


def usage_tokens(body):
    return int((body.get("usage") or {}).get("total_tokens", 0))
