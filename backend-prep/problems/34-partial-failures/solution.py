"""34. Concurrent fetch with partial failures: reference solution."""

from concurrent.futures import ThreadPoolExecutor

import httpx


def fetch_documents(client: httpx.Client, doc_ids: list[str], max_workers: int = 8) -> dict:
    def fetch(doc_id: str) -> dict:
        for attempt in (1, 2):
            try:
                resp = client.get(f"/v1/documents/{doc_id}")
            except httpx.HTTPError as exc:
                kind = "timeout" if isinstance(exc, httpx.TimeoutException) else "other"
                return {"id": doc_id, "error_type": kind, "message": f"{type(exc).__name__}: {exc}"}
            if resp.is_success:
                body = resp.json()
                return {k: body[k] for k in ("id", "title", "pages")}
            status = resp.status_code
            if status >= 500 and attempt == 1:
                continue
            kind = "not_found" if status == 404 else "server_error" if status >= 500 else "other"
            return {"id": doc_id, "error_type": kind, "message": f"{status}: {resp.text}"}

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        outcomes = list(pool.map(fetch, doc_ids))
    return {
        "results": {o["id"]: o for o in outcomes if "error_type" not in o},
        "failures": sorted((o for o in outcomes if "error_type" in o), key=lambda o: o["id"]),
    }


if __name__ == "__main__":
    from problem_api import make_api

    api = make_api(n_docs=5)
    api.script("GET /v1/documents/doc_002", [503, 503])
    api.script("GET /v1/documents/doc_003", [500])
    api.script("GET /v1/documents/doc_004", ["timeout"])
    out = fetch_documents(api.client(), ["doc_001", "doc_002", "doc_003", "doc_004", "doc_404"])
    print("results:", sorted(out["results"]))
    print("failures:", out["failures"])
