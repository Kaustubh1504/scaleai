"""M1. Annotator payouts: reference solution."""

from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Any

import httpx

from kit import RealClock


class ApiError(Exception):
    def __init__(self, status: int, path: str, message: str = ""):
        super().__init__(f"{status} on {path}: {message}")
        self.status = status
        self.path = path


class AuthError(ApiError):
    pass


# ------------------------------------------------------------------ client


class PayoutClient:
    def __init__(self, http: httpx.Client, client_id: str, client_secret: str, *,
                 clock: Any = None, rng: random.Random | None = None):
        self.http = http
        self.client_id = client_id
        self.client_secret = client_secret
        self.clock = clock or RealClock()
        self.rng = rng or random.Random()
        self.token = None

    def _send(self, method: str, path: str, **kw: Any) -> tuple[httpx.Response, Any]:
        failures = throttled = 0
        while True:
            try:
                resp = self.http.request(method, path, **kw)
            except httpx.TransportError:
                throttled = status = 0
            else:
                if resp.status_code == 429:
                    throttled += 1
                    if throttled >= 10:
                        raise ApiError(429, path, "rate limited 10 times in a row")
                    try:
                        self.clock.sleep(max(0.0, float(resp.headers.get("Retry-After", "1"))))
                    except ValueError:
                        self.clock.sleep(1.0)
                    continue
                throttled = 0
                status = resp.status_code
                if status not in (500, 502, 503, 504):
                    if not resp.is_success:
                        return resp, None
                    try:
                        return resp, resp.json()
                    except ValueError:
                        status = 0
            failures += 1
            if failures >= 4:
                raise ApiError(status, path, f"gave up after {failures} attempts")
            d = min(8.0, 0.5 * 2 ** (failures - 1))
            self.clock.sleep(self.rng.uniform(d / 2, d))

    def request(self, method: str, path: str, *, params: dict | None = None, json: Any = None,
                headers: dict | None = None) -> Any:
        refreshed = False
        while True:
            if self.token is None:
                creds = {"client_id": self.client_id, "client_secret": self.client_secret}
                try:
                    resp, body = self._send("POST", "/oauth/token", json=creds)
                except ApiError as exc:
                    raise AuthError(exc.status, exc.path, str(exc)) from exc
                if not resp.is_success:
                    raise AuthError(resp.status_code, "/oauth/token", resp.text[:200])
                self.token = body["access_token"]
            hdrs = {"Authorization": f"Bearer {self.token}", **(headers or {})}
            resp, body = self._send(method, path, params=params, json=json, headers=hdrs)
            if resp.status_code == 401:
                if refreshed:
                    raise AuthError(401, path, "still unauthorized after a token refresh")
                self.token, refreshed = None, True
                continue
            if not resp.is_success:
                raise ApiError(resp.status_code, path, resp.text[:200])
            return body

    def annotators(self) -> list[dict]:
        out, page = [], 1
        while True:
            body = self.request("GET", "/v1/annotators", params={"page": page, "per_page": 25})
            out += body["data"]
            if page >= body["total_pages"]:
                return out
            page += 1

    def tasks(self) -> list[dict]:
        out = []
        while True:
            body = self.request("GET", "/v1/tasks", params={"offset": len(out), "limit": 50})
            out += body["items"]
            if not body["items"] or len(out) >= body["total"]:
                return out

    def submissions(self) -> list[dict]:
        out, params = [], {"limit": 50}
        while True:
            body = self.request("GET", "/v1/submissions", params=params)
            out += body["results"]
            if not body.get("next_cursor"):
                return out
            params = {"limit": 50, "cursor": body["next_cursor"]}


# ------------------------------------------------------------------ report


def parse_ts(value: Any) -> datetime | None:
    if isinstance(value, str):
        s = value.strip()
        if s.isascii() and s.isdigit():
            value = int(s)
        else:
            try:
                dt = datetime.fromisoformat(s[:-1] + "+00:00" if s.endswith(("Z", "z")) else s)
            except ValueError:
                return None
            return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return datetime.fromtimestamp(value / 1000 if abs(value) >= 10**11 else value, timezone.utc)
    return None


def compute_payouts(client: PayoutClient, period_start: datetime, period_end: datetime) -> dict:
    annotators = {a["id"]: a for a in client.annotators()}
    rewards = {}
    for t in client.tasks():
        r = t.get("reward_cents")
        if isinstance(r, str) and r.strip().isascii() and r.strip().isdigit():
            r = int(r)
        rewards[t["id"]] = r if type(r) is int and r >= 0 else None

    rows, unknown, invalid, seen = {}, [], [], set()
    for sub in client.submissions():
        if sub["id"] in seen:
            continue
        seen.add(sub["id"])
        submitted = parse_ts(sub.get("submitted_at"))
        if submitted is None:
            invalid.append(sub["id"])
            continue
        if not period_start <= submitted < period_end:
            continue
        aid = sub["annotator_id"]
        if aid not in rows:
            ann = annotators.get(aid, {})
            h = ann.get("on_hold")
            if isinstance(h, str):
                h = h.strip().lower() not in ("false", "no", "0")
            rows[aid] = {"annotator_id": aid, "name": ann.get("name"),
                         "on_hold": not (h is None or h is False or type(h) is int and h == 0),
                         "approved": 0, "rejected": 0, "pending": 0, "amount_cents": 0}
        reviews = []
        for r in sub.get("reviews") or []:
            v, at = r.get("verdict"), parse_ts(r.get("reviewed_at"))
            v = v.strip().lower() if isinstance(v, str) else None
            if v in ("approved", "rejected") and at:
                reviews.append((at, str(r["id"]), v))
        # latest reviewed_at wins; ties go to the greatest review id
        verdict = max(reviews, key=lambda x: x[:2])[2] if reviews else "pending"
        rows[aid][verdict] += 1
        if verdict == "approved":
            if rewards.get(sub.get("task_id")) is None:
                unknown.append(sub["id"])
            else:
                rows[aid]["amount_cents"] += rewards[sub["task_id"]]

    ordered = [rows[k] for k in sorted(rows)]
    return {
        "period": f"{period_start:%Y-%m-%dT%H:%M:%SZ}/{period_end:%Y-%m-%dT%H:%M:%SZ}",
        "rows": ordered,
        "total_cents": sum(r["amount_cents"] for r in ordered if not r["on_hold"]),
        "held_cents": sum(r["amount_cents"] for r in ordered if r["on_hold"]),
        "unknown_reward": sorted(unknown),
        "invalid_submissions": sorted(invalid),
    }


# ------------------------------------------------------------------ publish


def publish_payouts(client: PayoutClient, report: dict) -> dict:
    out = {"paid": [], "failed": []}
    period = report["period"]
    for row in report["rows"]:
        if row["on_hold"] or row["amount_cents"] <= 0:
            continue
        aid = row["annotator_id"]
        body = {"annotator_id": aid, "period": period, "amount_cents": row["amount_cents"]}
        try:
            client.request("POST", "/v1/payouts", json=body,
                           headers={"Idempotency-Key": f"{period}:{aid}"})
            out["paid"].append(aid)
        except AuthError:
            raise
        except ApiError:
            out["failed"].append(aid)
    return out


if __name__ == "__main__":
    from kit import FakeClock
    from problem_api import CLIENT_ID, CLIENT_SECRET, make_api, messy_sample_data

    start, end = datetime(2024, 5, 1, tzinfo=timezone.utc), datetime(2024, 5, 15, tzinfo=timezone.utc)
    for data in (None, messy_sample_data()):
        clock = FakeClock()
        api = make_api(data, clock=clock)
        client = PayoutClient(api.client(), CLIENT_ID, CLIENT_SECRET, clock=clock, rng=random.Random(0))
        report = compute_payouts(client, start, end)
        print(report)
        print(publish_payouts(client, report), "stored:", len(api.payouts))
