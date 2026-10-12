"""Mock Workforce API for problem 19: three endpoints, three different envelopes."""

from __future__ import annotations

from kit import MockAPI

ANNOTATORS = [
    {"id": "w_004", "name": "Priya Raman", "locale": "en-IN"},
    {"id": "w_001", "name": "Diego Alvarez", "locale": "es-MX"},
    {"id": "w_007", "name": "Mei Lin", "locale": "zh-SG"},
]
REVIEWERS = [
    {"id": "w_006", "name": "Sam Okafor", "queue": "rlhf"},
    {"id": "w_002", "name": "Ana Silva", "queue": "ocr"},
]
LEADS = [
    {"id": "w_005", "name": "Jonas Berg", "team": "vision"},
    {"id": "w_003", "name": "Fatima Zahra", "team": "text"},
]


def make_api(*, annotators=None, reviewers=None, leads=None, leads_shape: str = "list",
             reviewers_shape: str = "results", clock=None) -> MockAPI:
    """
    leads_shape     : "list" (bare JSON list), "single" ({"data": {...}}, uses the first lead only),
                      "empty" ({"items": []}).
    reviewers_shape : "results" ({"results": {"items": [...], "count": n}}) or
                      "bad" ({"payload": [...], "ok": true}, an envelope nobody documented).
    """
    api = MockAPI(clock=clock)
    annotators = ANNOTATORS if annotators is None else annotators
    reviewers = REVIEWERS if reviewers is None else reviewers
    leads = LEADS if leads is None else leads

    @api.route("GET", "/v1/annotators")
    def list_annotators(req):
        return {"data": annotators, "meta": {"count": len(annotators)}}

    @api.route("GET", "/v1/reviewers")
    def list_reviewers(req):
        if reviewers_shape == "bad":
            return {"payload": reviewers, "ok": True}
        return {"results": {"items": reviewers, "count": len(reviewers)}}

    @api.route("GET", "/v1/leads")
    def list_leads(req):
        if leads_shape == "single":
            return {"data": leads[0]}
        if leads_shape == "empty":
            return {"items": []}
        return leads

    return api
