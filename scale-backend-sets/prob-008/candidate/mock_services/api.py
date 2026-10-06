"""The contributor platform API, running in-process.

    from mock_services.api import make_api
    api = make_api()                 # production-like data (seed 8), messy fields as API.md warns
    api = make_api(messy=False)      # the same platform with clean, canonical fields
    http = api.client()              # an httpx.Client wired to the mock (no sockets)
    http.post("/oauth/token", json={"client_id": CLIENT_ID, "client_secret": CLIENT_SECRET})

Read API.md for the endpoints. Useful knobs while testing your code:

    from shared.mock_rest import FaultConfig, RateLimitConfig
    make_api(latency_s=1.0)                                       # every request takes 1 s of clock time
    make_api(faults=FaultConfig(scripted={"GET /v1/reviews": [503, "429:3"]}))
    make_api(faults=FaultConfig(scripted={"POST /v1/results": ["malformed", "timeout"]}))
    make_api(rate_limit=RateLimitConfig(requests=5, window_s=2))
    api.insert("submissions", {...})     # add your own records (they are served like the others)
    api.log                              # every request the mock received
    api.canonical("results")             # every payout the sink has stored

Run it as a real server instead (optional):
    python -m mock_services.api_server --port 9300
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

import mock_services  # noqa: F401  (puts shared/ on sys.path)
from shared.fake_clock import Clock
from shared.mock_rest import (AuthConfig, FaultConfig, FieldMess, MockRestAPI, RateLimitConfig, ResourceConfig,
                              scale_records)

SEED = 8
CLIENT_ID = "finance"
CLIENT_SECRET = "finance-secret"
TIMESTAMP_MESS = ["epoch", "epoch_ms", "iso_naive", "iso_offset"]


def _iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def make_records(seed: int = SEED, *, messy: bool = True, annotators: int = 30, tasks: int = 300) -> dict:
    """The platform's data. Some submissions are reviewed more than once (re-reviews);
    in the messy build some tasks have no known reward."""
    data = scale_records(seed, annotators=annotators, tasks=tasks)
    rng = random.Random(f"earnings-reviews|{seed}")
    submitter = {s["id"]: s["annotator_id"] for s in data["submissions"]}
    extra = []
    for review in data["reviews"]:
        if rng.random() >= 0.3:
            continue
        first = datetime.fromisoformat(review["created_at"].replace("Z", "+00:00"))
        kind = rng.choice(["later", "earlier", "same"])
        moment = {"later": first + timedelta(minutes=rng.randint(30, 3000)),
                  "earlier": first - timedelta(minutes=rng.randint(1, 9)), "same": first}[kind]
        reviewer = rng.choice([a["id"] for a in data["annotators"] if a["id"] != submitter[review["submission_id"]]])
        extra.append({"id": f"rev_{len(data['reviews']) + len(extra) + 1:05d}",
                      "submission_id": review["submission_id"], "reviewer_id": reviewer,
                      "verdict": rng.choice(["approved", "rejected"]), "score": rng.randint(1, 5),
                      "comment": "Re-review.", "created_at": _iso(moment), "updated_at": _iso(moment)})
    data["reviews"].extend(extra)
    if messy:
        rewards = random.Random(f"earnings-rewards|{seed}")
        for task in data["tasks"]:
            roll = rewards.random()
            if roll < 0.06:
                task["reward_cents"] = None
            elif roll < 0.10:
                del task["reward_cents"]
    return data


def validate_payout(body: dict) -> str | None:
    if not isinstance(body.get("annotator_id"), str) or not body["annotator_id"]:
        return "annotator_id must be a non-empty string"
    if not isinstance(body.get("period"), str) or not body["period"]:
        return "period must be a non-empty string"
    amount = body.get("amount_cents")
    if isinstance(amount, bool) or not isinstance(amount, int) or amount <= 0:
        return "amount_cents must be a positive integer"
    return None


def make_resources(seed: int = SEED, *, messy: bool = True, annotators: int = 30, tasks: int = 300,
                   validator=validate_payout) -> list[ResourceConfig]:
    data = make_records(seed, messy=messy, annotators=annotators, tasks=tasks)
    mess = (lambda rules: rules) if messy else (lambda rules: [])
    return [
        ResourceConfig("annotators", data["annotators"], pagination="offset", default_page_size=10, max_page_size=20,
                       filters=("country", "level", "is_active"),
                       mess=mess([FieldMess("is_active", ["bool_str", "bool_int"], 0.4),
                                  FieldMess("hourly_rate_cents", ["str", "float"], 0.2),
                                  FieldMess("skills", ["csv"], 0.25),
                                  FieldMess("country", ["lower", "null"], 0.1)])),
        ResourceConfig("tasks", data["tasks"], pagination="cursor", default_page_size=25, max_page_size=100,
                       filters=("project_id", "status", "is_gold"),
                       mess=mess([FieldMess("reward_cents", ["str"], 0.25),
                                  FieldMess("priority", ["str"], 0.15),
                                  FieldMess("tags", ["csv", "missing"], 0.2),
                                  FieldMess("created_at", TIMESTAMP_MESS, 0.2),
                                  FieldMess("payload.dimensions", ["missing"], 0.1),
                                  FieldMess("status", ["upper", "padded"], 0.1)])),
        ResourceConfig("submissions", data["submissions"], pagination="cursor", default_page_size=50,
                       max_page_size=100, filters=("task_id", "annotator_id"), parent=("tasks", "task_id"),
                       mess=mess([FieldMess("submitted_at", TIMESTAMP_MESS, 0.4),
                                  FieldMess("answer.label", ["upper", "padded"], 0.3),
                                  FieldMess("answer.confidence", ["str", "null"], 0.15),
                                  FieldMess("answer.boxes", ["missing", "null"], 0.1),
                                  FieldMess("duration_s", ["str"], 0.15)])),
        ResourceConfig("reviews", data["reviews"], pagination="page", default_page_size=20, max_page_size=50,
                       filters=("reviewer_id", "verdict", "submission_id"), parent=("submissions", "submission_id"),
                       mess=mess([FieldMess("verdict", ["upper", "padded"], 0.3),
                                  FieldMess("created_at", TIMESTAMP_MESS, 0.4),
                                  FieldMess("score", ["str"], 0.15),
                                  FieldMess("comment", ["missing", "empty_str"], 0.3)])),
        ResourceConfig("results", [], pagination="page", default_page_size=20, max_page_size=50, writable=True,
                       updated_field=None, validator=validator),
    ]


def make_api(seed: int = SEED, clock: Clock | None = None, *, messy: bool = True, annotators: int = 30,
             tasks: int = 300, token_ttl_s: float = 300.0, latency_s: float = 0.0, faults: FaultConfig | None = None,
             rate_limit: RateLimitConfig | None = None, on_request=None) -> MockRestAPI:
    faults = faults or FaultConfig(seed=seed)
    faults.latency_s = faults.latency_s or latency_s
    return MockRestAPI(make_resources(seed, messy=messy, annotators=annotators, tasks=tasks), clock=clock,
                       faults=faults, rate_limit=rate_limit, on_request=on_request,
                       auth=AuthConfig(client_id=CLIENT_ID, client_secret=CLIENT_SECRET, token_ttl_s=token_ttl_s))
