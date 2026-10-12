"""40. Refactor a messy payout script: reference solution."""

from __future__ import annotations

import json
import logging
from collections import Counter
from dataclasses import asdict, dataclass
from typing import Iterator, Mapping

import httpx

logger = logging.getLogger(__name__)

RATES_CENTS = {"bbox": 12, "classify": 5, "transcribe": 30}
SENIOR_PCT = 125


class ConfigError(Exception):
    pass


class ApiError(Exception):
    def __init__(self, status: int, path: str):
        super().__init__(f"{status} on {path}")
        self.status = status
        self.path = path


@dataclass(frozen=True)
class Config:
    base_url: str
    api_key: str
    timeout_s: float = 10.0
    per_page: int = 50


@dataclass(frozen=True)
class Payout:
    annotator_id: str
    name: str
    tasks: int
    amount_cents: int


def load_config(env: Mapping[str, str]) -> Config:
    for name in ("PAYOUT_API_URL", "PAYOUT_API_KEY"):
        if not env.get(name, "").strip():
            raise ConfigError(f"{name} is required")
    try:
        timeout_s = float(env.get("PAYOUT_TIMEOUT_S", "").strip() or 10)
    except ValueError:
        timeout_s = 0
    if not timeout_s > 0:
        raise ConfigError("PAYOUT_TIMEOUT_S must be a number > 0")
    try:
        per_page = int(env.get("PAYOUT_PER_PAGE", "").strip() or 50)
    except ValueError:
        per_page = 0
    if not 1 <= per_page <= 100:
        raise ConfigError("PAYOUT_PER_PAGE must be an integer in 1..100")
    return Config(env["PAYOUT_API_URL"].strip().rstrip("/"), env["PAYOUT_API_KEY"].strip(),
                  timeout_s, per_page)


class ApiClient:
    def __init__(self, http: httpx.Client, config: Config):
        self.http = http
        self.config = config

    def paginate(self, path: str) -> Iterator[dict]:
        page = 1
        while True:
            logger.debug("GET %s page=%d", path, page)
            resp = self.http.get(
                path,
                params={"page": page, "per_page": self.config.per_page},
                headers={"Authorization": f"Bearer {self.config.api_key}"},
            )
            try:
                body = resp.raise_for_status().json()
            except (httpx.HTTPStatusError, ValueError):
                raise ApiError(resp.status_code, path) from None
            yield from body["data"]
            if page >= body["total_pages"]:
                return
            page += 1


def compute_payouts(annotators: list[dict], submissions: list[dict]) -> list[Payout]:
    active = {a["id"]: a for a in annotators if a["active"]}
    tasks, cents = Counter(), Counter()
    for sub in submissions:
        aid = sub["annotator_id"]
        if sub["status"] != "accepted" or aid not in active:
            continue
        if sub["task_type"] not in RATES_CENTS:
            logger.warning("skipping %s: unknown task type %r", sub["id"], sub["task_type"])
            continue
        tasks[aid] += 1
        cents[aid] += RATES_CENTS[sub["task_type"]]
    payouts = [
        Payout(aid, active[aid]["name"], tasks[aid],
               (c * SENIOR_PCT + 50) // 100 if active[aid]["level"] == "senior" else c)  # half up
        for aid, c in cents.items()
    ]
    return sorted(payouts, key=lambda p: (-p.amount_cents, p.annotator_id))


def _dollars(cents: int) -> str:
    return f"${cents // 100}.{cents % 100:02d}"


def format_summary(payouts: list[Payout]) -> str:
    lines = ["PAYOUT SUMMARY"]
    lines += [f"{p.annotator_id}  {p.name:<20} {p.tasks:>4} tasks  {_dollars(p.amount_cents)}"
              for p in payouts]
    total = sum(p.amount_cents for p in payouts)
    lines.append(f"TOTAL {_dollars(total)} across {len(payouts)} annotators")
    return "\n".join(lines)


def main(argv: list[str], env: Mapping[str, str], http: httpx.Client | None = None) -> int:
    try:
        config = load_config(env)
    except ConfigError as exc:
        logger.error("bad config: %s", exc)
        return 2
    client = http if http is not None else httpx.Client(base_url=config.base_url,
                                                        timeout=config.timeout_s)
    try:
        api = ApiClient(client, config)
        annotators = list(api.paginate("/v1/annotators"))
        payouts = compute_payouts(annotators, list(api.paginate("/v1/submissions")))
    except ApiError as exc:
        logger.error("payout run failed: %s", exc)
        return 1
    finally:
        if http is None:
            client.close()
    if "--json" in argv:
        print(json.dumps([asdict(p) for p in payouts], indent=2))
    else:
        print(format_summary(payouts))
    return 0


if __name__ == "__main__":
    import sys

    from problem_api import ENV, make_api

    logging.basicConfig(level=logging.INFO)
    sys.exit(main(sys.argv[1:], ENV, make_api().client()))
