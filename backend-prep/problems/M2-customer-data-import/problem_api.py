"""Mock company-directory API and sample data for M2.

    api = make_api()                         # the sample directory below
    api = make_api({"acme.io": {...}})       # your own directory (domain -> company)
    api = make_api(real_latency_s=0.02)      # really sleeps per request (Part 3 concurrency)

GET /v1/companies/{domain} with header X-API-Key -> 200 company | 404 | 401.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from kit import FakeClock, MockAPI, error_response

API_KEY = "key_enrich_42"
SAMPLE_CSV = Path(__file__).resolve().parent / "data" / "customers.csv"

COMPANIES = {
    "acme.io": {"name": "Acme Corp", "industry": "Manufacturing", "employee_count": 1200},
    "navy.example": {"name": "US Navy", "industry": "Government", "employee_count": 340000},
    "kernel.example": {"name": "Kernel Org", "industry": "Software", "employee_count": 40},
    "bletchley.example": {"name": "Bletchley Park", "industry": "Research", "employee_count": 9000},
    "bell-labs.example": {"name": "Bell Labs", "industry": "Research", "employee_count": 15000},
    "mit.example": {"name": "MIT", "industry": "Education", "employee_count": 13000},
    "nasa.example": {"name": "NASA", "industry": "Aerospace", "employee_count": 18000},
}


def company(name: str, industry: str = "Software", employees: int = 10) -> dict:
    return {"name": name, "industry": industry, "employee_count": employees}


def make_api(companies: dict[str, dict] | None = None, *, clock: Any = None,
             real_latency_s: float = 0.0) -> MockAPI:
    clock = clock if clock is not None else FakeClock()
    directory = dict(COMPANIES if companies is None else companies)
    api = MockAPI(clock=clock, real_latency_s=real_latency_s)
    api.companies = directory

    @api.route("GET", "/v1/companies/{domain}")
    def get_company(req, domain):
        if req.header("x-api-key") != API_KEY:
            return error_response(401, "missing or invalid X-API-Key")
        found = directory.get(domain)
        if found is None:
            return error_response(404, f"no company for {domain}")
        return {"domain": domain, **found}

    return api


def lookups(api: MockAPI) -> list[str]:
    """Domains requested from /v1/companies, in request order."""
    return [c.path.rsplit("/", 1)[-1] for c in api.log if c.path.startswith("/v1/companies/")]
