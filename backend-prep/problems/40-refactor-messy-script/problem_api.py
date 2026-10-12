"""Mock Payouts API for problem 40. Tests and your __main__ block both use make_api()."""

from __future__ import annotations

from kit import MockAPI, error_response, paginate_pages

API_KEY = "sk_live_payouts_42"
ENV = {"PAYOUT_API_URL": "https://api.example.test", "PAYOUT_API_KEY": API_KEY}

ANNOTATORS = [
    {"id": "ann_001", "name": "Ada Okafor", "level": "senior", "active": True},
    {"id": "ann_002", "name": "Bo Lindqvist", "level": "junior", "active": True},
    {"id": "ann_003", "name": "Cy Tanaka", "level": "junior", "active": False},
    {"id": "ann_004", "name": "Di Moreau", "level": "senior", "active": True},
    {"id": "ann_005", "name": "Eli Navarro", "level": "junior", "active": True},
    {"id": "ann_006", "name": "Fay Chen", "level": "junior", "active": True},
    {"id": "ann_007", "name": "Gus Albright", "level": "senior", "active": True},
]

_TYPES = ["bbox", "classify", "transcribe", "bbox", "classify", "polygon"]
_STATUSES = ["accepted", "accepted", "rejected", "accepted", "pending"]
_WHO = ["ann_001", "ann_002", "ann_003", "ann_004", "ann_005", "ann_002", "ann_001", "ann_009", "ann_007"]


def make_submissions(n: int = 47) -> list[dict]:
    return [{"id": f"sub_{i:03d}", "annotator_id": _WHO[i % len(_WHO)], "task_type": _TYPES[(i * 7) % len(_TYPES)],
             "status": _STATUSES[(i * 3) % len(_STATUSES)]} for i in range(1, n + 1)]


def make_api(annotators: list[dict] | None = None, submissions: list[dict] | None = None, clock=None) -> MockAPI:
    """GET /v1/annotators and GET /v1/submissions, page-number pagination, Bearer auth."""
    api = MockAPI(clock=clock)
    api.annotators = list(ANNOTATORS if annotators is None else annotators)
    api.submissions = make_submissions() if submissions is None else list(submissions)

    def lister(items: list[dict]):
        def handler(req):
            if req.header("authorization") != f"Bearer {API_KEY}":
                return error_response(401, "missing or invalid bearer token")
            try:
                page = int(req.params.get("page", "1"))
                per_page = int(req.params.get("per_page", "20"))
            except ValueError:
                return error_response(400, "page and per_page must be integers")
            if page < 1 or not 1 <= per_page <= 100:
                return error_response(400, "page >= 1 and 1 <= per_page <= 100")
            return paginate_pages(items, page, per_page)
        return handler

    api.add_route("GET", "/v1/annotators", lister(api.annotators))
    api.add_route("GET", "/v1/submissions", lister(api.submissions))
    return api
