"""Part 2: Customer API lookups with retries, caching and error mapping."""

import json
import logging
from pathlib import Path

import pytest
from conftest import CUSTOMER_KEY, HERE, enrich, keyed

EXPECTED = json.loads((HERE / "expected_sample.json").read_text())
PART2_CODES = {"missing_customer_id", "unknown_customer", "customer_lookup_failed"}


def customers_by_ticket():
    return {r["ticket_id"]: r["customer"] for r in json.loads(Path("output/tickets.json").read_text())}


def test_customers_exact(client):
    r = enrich(client)
    assert r.status_code == 200, r.text
    assert customers_by_ticket() == {r["ticket_id"]: r["customer"] for r in EXPECTED["rows"]}


def test_customer_errors(client):
    got = enrich(client).json()["errors"]
    assert keyed(got, PART2_CODES) == [
        (5, "K005", "unknown_customer"),
        (6, "K006", "missing_customer_id"),
        (9, "K007", "customer_lookup_failed"),
        (14, "K011", "customer_lookup_failed"),
    ]


@pytest.mark.parametrize("cid,calls", [
    ("C01", 1),   # two tickets (K001, K004 with padded id), looked up once
    ("C02", 2),   # 429 then ok; shared by K002 and K010, still one logical lookup
    ("C03", 3),   # 500, 503, ok
    ("C04", 3),   # 503 forever: 1 try + 2 retries
    ("C05", 2),   # timeout then ok
    ("C99", 1),   # 404: not retried
    ("C07", 1),   # 200 with an invalid tier: not retried
])
def test_call_counts(client, customers, cid, calls):
    enrich(client)
    assert customers.count(cid) == calls


def test_total_calls_and_no_call_for_empty_id(client, customers):
    enrich(client)
    assert customers.count(None) == 14
    assert "" not in {c["id"] for c in customers.calls}


def test_api_key_header(client, customers):
    enrich(client)
    assert customers.calls and all(c["headers"].get("x-api-key") == CUSTOMER_KEY for c in customers.calls)


def test_auth_error_is_not_retried(client, customers, monkeypatch):
    monkeypatch.setenv("CUSTOMER_API_KEY", "wrong-key")
    r = enrich(client)
    assert r.status_code == 200
    assert set(map(str, customers_by_ticket().values())) == {"None"}
    assert customers.count(None) == 8  # one 401 per distinct customer id
    assert sum(e["error"] == "customer_lookup_failed" for e in r.json()["errors"]) == 10


@pytest.mark.parametrize("var", ["CUSTOMER_API_URL", "CUSTOMER_API_KEY"])
def test_missing_config_is_503(client, monkeypatch, var):
    monkeypatch.delenv(var)
    assert enrich(client).status_code == 503
    assert not Path("output/tickets.json").exists()


def test_keys_never_leak(client, caplog, capfd):
    caplog.set_level(logging.DEBUG)
    r = enrich(client)
    out, err = capfd.readouterr()
    blob = caplog.text + out + err + r.text + Path("output/tickets.json").read_text()
    assert CUSTOMER_KEY not in blob
