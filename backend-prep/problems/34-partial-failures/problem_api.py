"""Mock Documents API for problem 34. Tests and your __main__ block both use make_api().

Use ``api.script(f"GET /v1/documents/{doc_id}", [...])`` to make one document
fail: 500/503 (server error), 404, 403, "timeout" (httpx.ReadTimeout) or
"connect" (httpx.ConnectError). ``broken`` ids return a record with no "title".
"""

from __future__ import annotations

from kit import MockAPI, error_response


def doc_id(i: int) -> str:
    return f"doc_{i:03d}"


def make_doc(i: int) -> dict:
    return {
        "id": doc_id(i),
        "title": f"Contract {i}",
        "pages": 1 + (i * 3) % 17,
        "customer_id": f"cus_{i % 4}",
        "storage_url": f"s3://docs/{doc_id(i)}.pdf",
    }


def make_api(n_docs: int = 20, *, real_latency_s: float = 0.0, broken: tuple[str, ...] = ()) -> MockAPI:
    """
    n_docs         : doc_001 .. doc_<n> exist; any other id is a real 404.
    real_latency_s : real time per request (only the concurrency test sets it).
    broken         : ids whose record comes back without a "title" (a contract violation).
    """
    api = MockAPI(real_latency_s=real_latency_s)
    docs = {doc_id(i): make_doc(i) for i in range(1, n_docs + 1)}
    api.docs = docs

    @api.route("GET", "/v1/documents/{did}")
    def get_document(req, did):
        if did not in docs:
            return error_response(404, f"document {did} not found")
        record = dict(docs[did])
        if did in broken:
            del record["title"]
        return record

    return api
