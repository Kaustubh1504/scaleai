"""34. Concurrent fetch with partial failures

Template: imports, constants, exceptions and signatures are here.
Fill in every `raise NotImplementedError` (add your own helpers as needed)."""

from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
import httpx

FIELDS = ("id", "title", "pages")


def fetch_one(client: httpx.Client, doc_id: str) -> tuple[str, dict]:
    """Return ("ok", record) or ("fail", failure). Only HTTP-level problems become failures."""
    raise NotImplementedError


def fetch_documents(client: httpx.Client, doc_ids: list[str], max_workers: int = 8) -> dict:
    raise NotImplementedError


if __name__ == "__main__":
    from problem_api import make_api

    api = make_api(n_docs=5)
    api.script("GET /v1/documents/doc_002", [503, 503])
    api.script("GET /v1/documents/doc_003", [500])  # retried once, then succeeds
    api.script("GET /v1/documents/doc_004", ["timeout"])
    out = fetch_documents(api.client(), ["doc_001", "doc_002", "doc_003", "doc_004", "doc_404"])
    print("results:", sorted(out["results"]))
    for f in out["failures"]:
        print("failure:", f)
