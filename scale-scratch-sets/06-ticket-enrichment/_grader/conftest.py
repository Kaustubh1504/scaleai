"""Hidden acceptance tests for 06-ticket-enrichment.

    python -m pytest _grader -q                                  # grade your code (problem root)
    SOLUTION_DIR=_grader/reference python -m pytest _grader -q   # self-check the grader

Both external APIs are faked locally: the Customer API by mock_customers.py and
OpenAI by _grader_shared/mock_llm.py (via OPENAI_BASE_URL).
"""

from __future__ import annotations

import importlib
import os
import re
import shutil
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
PROBLEM = HERE.parent
SOLUTION_DIR = Path(os.environ.get("SOLUTION_DIR", PROBLEM)).resolve()
sys.path.insert(0, str(SOLUTION_DIR))
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(PROBLEM.parent / "_grader_shared"))

from mock_customers import MockCustomers  # noqa: E402
from mock_llm import MockLLM  # noqa: E402

DATA = HERE / "data"
LLM_KEY = "sk-test-SECRET-06llm-c0ffee"
CUSTOMER_KEY = "cust-SECRET-06-beef"
TIERS = ["free", "pro", "enterprise"]
URGENCIES = ["low", "medium", "high"]


def cust(cid, name, tier, region="us"):
    return ("json", {"customer_id": cid, "name": name, "tier": tier, "region": region})


CUSTOMER_SCRIPT = {
    "C01": [cust("C01", "Acme Corp", "enterprise", "eu")],
    "C02": [("status", 429), cust("C02", "Bluebird Labs", "pro")],
    "C03": [("status", 500), ("status", 503), cust("C03", "Cobalt Bank", "enterprise")],
    "C99": [("status", 404)],
    "C04": [("status", 503)],
    "C05": [("sleep", 1.5, cust("C05", "Dot Studio", "free")), cust("C05", "Dot Studio", "free")],
    "C06": [cust("C06", "Echo Games", "free", "apac")],
    "C07": [cust("C07", "Fern Health", "platinum")],
}


def customer_default(cid):
    m = re.fullmatch(r"L(\d{2})", cid)
    if m:
        n = int(m.group(1))
        return cust(cid, f"Large {n}", TIERS[n % 3])
    return ("status", 404)


U = lambda u: ("json", {"urgency": u})  # noqa: E731
LLM_SCRIPT = {
    "Cannot log in": [U("medium")],
    "Billing question, invoice 4471": [U("low")],
    "Production API down": [U("high")],
    "Feature request: dark mode": [("status", 429), U("low")],
    "Where is my order": [("status", 500), U("medium")],
    "Question about export": [U("low")],
    "Data export slow": [("text", "I'd say this is medium urgency."), U("medium")],
    "Webhooks failing": [("status", 503)],
    "Refund ticket 8812": [U("critical")],
    "Typo on pricing page": [("sleep", 1.5, U("low")), U("low")],
    "Account locked": [U("high")],
}


def llm_default(text):
    m = re.search(r"TKT-(\d{4})", text)
    return U(URGENCIES[int(m.group(1)) % 3] if m else "low")


@pytest.fixture
def workdir(tmp_path, monkeypatch):
    (tmp_path / "data").mkdir()
    (tmp_path / "output").mkdir()
    for f in DATA.glob("*.csv"):
        shutil.copy(f, tmp_path / "data" / f.name)
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def customers(monkeypatch):
    mock = MockCustomers(CUSTOMER_KEY, CUSTOMER_SCRIPT, default=customer_default).start()
    monkeypatch.setenv("CUSTOMER_API_URL", mock.url)
    monkeypatch.setenv("CUSTOMER_API_KEY", CUSTOMER_KEY)
    monkeypatch.setenv("CUSTOMER_TIMEOUT", "0.5")
    monkeypatch.setenv("CUSTOMER_BACKOFF_BASE", "0.01")
    yield mock
    mock.stop()


@pytest.fixture
def llm(monkeypatch):
    mock = MockLLM(LLM_KEY, LLM_SCRIPT, default=llm_default).start()
    monkeypatch.setenv("OPENAI_API_KEY", LLM_KEY)
    monkeypatch.setenv("OPENAI_BASE_URL", mock.url)
    monkeypatch.setenv("LLM_TIMEOUT", "0.5")
    monkeypatch.setenv("LLM_BACKOFF_BASE", "0.01")
    yield mock
    mock.stop()


@pytest.fixture
def client(workdir, customers, llm):
    from fastapi.testclient import TestClient

    mod = importlib.import_module("app.main")
    with TestClient(mod.app) as c:
        yield c


def enrich(client, tickets="data/tickets.csv", output="output/tickets.json"):
    return client.post("/enrich", json={"tickets_path": tickets, "output_path": output})


def keyed(errors, codes):
    return sorted((e["row"], e["id"], e["error"]) for e in errors if e["error"] in codes)
