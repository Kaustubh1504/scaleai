"""Part 3: LLM urgency (using the customer tier), SLA, bounded concurrency, order."""

import csv
import json
import logging
import time
from pathlib import Path

import pytest
from conftest import HERE, LLM_KEY, TIERS, URGENCIES, enrich, keyed

EXPECTED = json.loads((HERE / "expected_sample.json").read_text())

SLA = {
    "enterprise": {"high": 1, "medium": 4, "low": 24},
    "pro": {"high": 4, "medium": 12, "low": 48},
    "free": {"high": 24, "medium": 48, "low": 72},
}


def rows(name="tickets.json"):
    return json.loads(Path("output", name).read_text())


def test_urgency_and_sla_exact(client):
    r = enrich(client)
    assert r.status_code == 200, r.text
    got = {x["ticket_id"]: (x["urgency"], x["sla_hours"]) for x in rows()}
    assert got == {x["ticket_id"]: (x["urgency"], x["sla_hours"]) for x in EXPECTED["rows"]}


def test_urgency_errors(client):
    got = enrich(client).json()["errors"]
    assert keyed(got, {"urgency_failed"}) == [(10, "K008", "urgency_failed"), (12, "K009", "urgency_failed")]


@pytest.mark.parametrize("marker,calls", [
    ("Cannot log in", 1),
    ("Feature request: dark mode", 2),   # 429 then ok
    ("Where is my order", 2),            # 500 then ok
    ("Typo on pricing page", 2),         # timeout then ok
    ("Webhooks failing", 4),             # 503 forever: 1 try + 3 retries
    ("Data export slow", 2),             # not JSON once, then ok
    ("Refund ticket 8812", 2),           # injection -> "critical" twice -> fallback
])
def test_llm_call_counts(client, llm, marker, calls):
    enrich(client)
    assert llm.count(marker) == calls


def test_one_logical_call_per_ticket(client, llm):
    enrich(client)
    assert llm.count(None) == 19


def test_prompt_has_ticket_text_and_tier(client, llm):
    enrich(client)
    def text(marker):
        found = [c["text"] for c in llm.calls if c["marker"] == marker]
        assert found, marker
        return found[0]

    ent, free = text("Production API down"), text("Question about export")  # enterprise vs no customer
    assert "All requests return 500 since 09:00" in ent
    # the tier must come from the lookup, not just a list of tiers in the system prompt
    assert ent.count("enterprise") > free.count("enterprise")


def test_unknown_customer_uses_free_sla(client):
    enrich(client)
    by_id = {x["ticket_id"]: x for x in rows()}
    assert by_id["K005"]["customer"] is None and by_id["K005"]["sla_hours"] == 48
    assert by_id["K006"]["customer"] is None and by_id["K006"]["sla_hours"] == 72


def test_missing_openai_key_is_503(client, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY")
    assert enrich(client).status_code == 503


def test_openai_key_never_leaks(client, caplog, capfd):
    caplog.set_level(logging.DEBUG)
    r = enrich(client)
    out, err = capfd.readouterr()
    assert LLM_KEY not in caplog.text + out + err + r.text + Path("output/tickets.json").read_text()


# ---------------------------------------------------------------- scale


def large(client):
    return enrich(client, tickets="data/tickets_large.csv", output="output/large.json")


def expected_large():
    with open("data/tickets_large.csv", encoding="utf-8") as f:
        out = []
        for r in csv.DictReader(f):
            urg = URGENCIES[int(r["ticket_id"][1:]) % 3]
            tier = TIERS[int(r["customer_id"][1:]) % 3]
            out.append((r["ticket_id"], tier, urg, SLA[tier][urg]))
        return out


def test_large_order_and_values(client):
    r = large(client)
    assert r.status_code == 200, r.text
    assert r.json()["rows_written"] == 300
    got = [(x["ticket_id"], x["customer"]["tier"], x["urgency"], x["sla_hours"]) for x in rows("large.json")]
    assert got == expected_large()


def test_large_each_customer_looked_up_once(client, customers):
    large(client)
    assert customers.count(None) == 20


def test_bounded_parallel_llm(client, llm):
    llm.delay = 0.05
    t0 = time.monotonic()
    assert large(client).status_code == 200
    elapsed = time.monotonic() - t0
    assert llm.peak <= 5, f"{llm.peak} LLM requests in flight at once (max 5)"
    assert llm.peak >= 3, f"only {llm.peak} LLM requests in flight at once: calls are not parallel"
    assert elapsed < 8, f"took {elapsed:.1f}s; sequential would be ~15s"


def test_bounded_parallel_customers(client, customers):
    customers.delay = 0.05
    assert large(client).status_code == 200
    assert customers.peak <= 5, f"{customers.peak} customer requests in flight at once (max 5)"
    assert customers.peak >= 3, f"only {customers.peak} customer requests in flight at once: not parallel"
