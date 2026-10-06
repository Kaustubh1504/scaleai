"""Configuration objects for ``MockRestAPI``."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

PAGINATION_STYLES = ("page", "offset", "cursor", "none")

# Default envelope keys per pagination style. Override any of them per
# resource with ``ResourceConfig.envelope={"data": "rows"}``.
DEFAULT_ENVELOPES = {
    "cursor": {"data": "data", "next_cursor": "next_cursor"},
    "page": {"data": "results", "page": "page", "per_page": "per_page", "total": "total", "total_pages": "total_pages"},
    "offset": {"data": "items", "offset": "offset", "limit": "limit", "total": "total"},
}


@dataclass
class FieldMess:
    """Make a field inconsistent in the rendered API output.

    ``path`` is a dotted path into the record (``"payload.dimensions.width"``);
    ``"boxes[].label"`` applies to every element of a list. For each record a
    deterministic draw (seed, resource, record id, path) decides whether the
    field is messed (probability ``rate``) and which variant is used. The same
    record therefore always looks the same: the data is messy, not flaky.
    Variant names are listed in ``messy.VARIANTS``.
    """

    path: str
    variants: list[str]
    rate: float = 0.2


@dataclass
class ResourceConfig:
    name: str  # URL segment: GET /v1/<name>
    records: list[dict] = field(default_factory=list)
    id_field: str = "id"
    pagination: str = "cursor"
    default_page_size: int = 20
    max_page_size: int = 100
    envelope: dict[str, str] = field(default_factory=dict)  # default key -> custom key
    filters: tuple[str, ...] = ()  # fields usable as ?field=value (dotted paths allowed)
    parent: tuple[str, str] | None = None  # ("projects", "project_id") enables /v1/projects/{id}/<name>
    sort_field: str | None = None  # default: id_field
    updated_field: str | None = "updated_at"  # enables ?updated_since=<iso>
    mess: list[FieldMess] = field(default_factory=list)
    writable: bool = False  # POST /v1/<name> stores the JSON body (a results "sink")
    validator: Callable[[dict], str | None] | None = None  # for writable: return an error message to reject (422)

    def __post_init__(self) -> None:
        if self.pagination not in PAGINATION_STYLES:
            raise ValueError(f"pagination must be one of {PAGINATION_STYLES}")
        if not 1 <= self.default_page_size <= self.max_page_size:
            raise ValueError("default_page_size must be between 1 and max_page_size")


@dataclass
class AuthConfig:
    """``oauth``: POST /oauth/token with client credentials (JSON or form) -> bearer token.
    ``api_key``: header ``X-API-Key``. ``none``: no auth."""

    mode: str = "oauth"
    client_id: str = "client"
    client_secret: str = "secret"
    api_key: str = "key_live_123"
    token_ttl_s: float = 300.0
    max_requests_per_token: int | None = None  # token dies after this many API requests
    refresh_tokens: bool = True  # issue single-use refresh tokens (grant_type=refresh_token)


@dataclass
class RateLimitConfig:
    """Sliding window over authenticated API requests (the token endpoint is exempt)."""

    requests: int = 10
    window_s: float = 1.0
    scope: str = "client"  # "client": per credential (refreshing a token does not reset it) | "global"
    retry_after_format: str = "seconds"  # "seconds" | "http-date" | "none" (header omitted)
    headers: bool = True  # X-RateLimit-Limit / -Remaining / -Reset on every API response


@dataclass
class FaultConfig:
    """Random and scripted failures.

    Random draws come from ``Random(f"{seed}|{request key}|{attempt}")`` where the
    key is method + path + sorted query (not the token) and ``attempt`` counts
    requests with that key. Retrying the same URL gets a fresh draw, and runs are
    reproducible regardless of how different URLs interleave across threads.

    ``scripted`` maps a substring of ``"GET /v1/tasks?cursor=..."`` to outcomes
    for successive matching requests: an int status, ``"429:<s>"``, ``"timeout"``,
    ``"malformed"`` (200 with a truncated JSON body) or ``"ok"``.
    """

    seed: int = 0
    failure_rate: float = 0.0  # 500/502/503
    rate_limit_rate: float = 0.0  # random 429 with retry_after_s
    retry_after_s: float = 1.0
    malformed_rate: float = 0.0
    latency_s: float = 0.0
    slow_rate: float = 0.0  # this fraction of requests takes slow_latency_s
    slow_latency_s: float = 30.0
    scripted: dict[str, list[int | str]] = field(default_factory=dict)
    faults_on_auth: bool = True  # random faults also hit the token endpoint
