"""Part 3: backoff, Retry-After, bounded concurrency, idempotent re-runs."""

import asyncio
import threading
import time

from conftest import make_llm, upload_id_for
from shared.mock_llm import LLMConfig

ONE_TICKET = ("ticket_id,customer_email,subject,body,created_at\n"
              "A,a@b.co,Idea,It would be great to have a dark mode feature.,2024-01-01T00:00:00Z\n").encode()


def classify(client, upload_id):
    resp = client.post(f"/uploads/{upload_id}/classify")
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_exponential_backoff_with_jitter(make_client, clock):
    llm = make_llm(LLMConfig(prompt_faults={"dark mode": ["server_error", "malformed"]}), clock)
    client = make_client(llm=llm)
    result = classify(client, upload_id_for(client, "t.csv", ONE_TICKET))["results"][0]
    assert (result["status"], result["attempts"]) == ("classified", 3)
    assert len(clock.sleeps) == 2
    assert 0.25 <= clock.sleeps[0] <= 0.5
    assert 0.5 <= clock.sleeps[1] <= 1.0


def test_jitter_is_random(make_client, clock):
    llm = make_llm(LLMConfig(prompt_faults={f"body {i}": ["server_error"] for i in range(8)}), clock)
    client = make_client(llm=llm)
    content = ("ticket_id,customer_email,subject,body,created_at\n" + "".join(
        f"T{i},a@b.co,s,body {i},2024-01-01T00:00:00Z\n" for i in range(8))).encode()
    classify(client, upload_id_for(client, "t.csv", content))
    assert len(clock.sleeps) == 8
    assert all(0.25 <= s <= 0.5 for s in clock.sleeps)
    assert len(set(clock.sleeps)) > 1


def test_rate_limit_waits_retry_after(make_client, clock):
    llm = make_llm(LLMConfig(prompt_faults={"dark mode": ["rate_limit", "rate_limit"]}, retry_after_s=2.5), clock)
    client = make_client(llm=llm)
    result = classify(client, upload_id_for(client, "t.csv", ONE_TICKET))["results"][0]
    assert (result["status"], result["attempts"]) == ("classified", 3)
    assert clock.sleeps == [2.5, 2.5]


def test_no_sleep_after_final_failure_or_non_retryable(make_client, clock):
    llm = make_llm(LLMConfig(prompt_faults={"dark mode": ["server_error"] * 3}), clock)
    client = make_client(llm=llm)
    assert classify(client, upload_id_for(client, "t.csv", ONE_TICKET))["results"][0]["status"] == "failed"
    assert len(clock.sleeps) == 2

    clock.sleeps.clear()
    llm = make_llm(LLMConfig(max_context_tokens=3), clock)
    client = make_client(llm=llm)
    assert classify(client, upload_id_for(client, "t.csv", ONE_TICKET))["results"][0]["attempts"] == 1
    assert clock.sleeps == []


class ConcurrencyProbe:
    """Records how many calls are in flight at once. Works for sync and async callers."""

    def __init__(self, inner, hold_s=0.05):
        self.inner, self.hold_s = inner, hold_s
        self.lock, self.active, self.peak, self.calls = threading.Lock(), 0, 0, 0

    def _enter(self):
        with self.lock:
            self.active += 1
            self.calls += 1
            self.peak = max(self.peak, self.active)

    def _exit(self):
        with self.lock:
            self.active -= 1

    def complete(self, prompt, **kwargs):
        self._enter()
        try:
            time.sleep(self.hold_s)
            return self.inner.complete(prompt, **kwargs)
        finally:
            self._exit()

    async def acomplete(self, prompt, **kwargs):
        self._enter()
        try:
            await asyncio.sleep(self.hold_s)
            return await self.inner.acomplete(prompt, **kwargs)
        finally:
            self._exit()


def many_tickets(n):
    return ("ticket_id,customer_email,subject,body,created_at\n" + "".join(
        f"T{i:03d},a@b.co,Refund {i},Please refund invoice {i}.,2024-01-01T00:00:00Z\n" for i in range(n))).encode()


def test_concurrency_is_used_and_bounded(make_client, clock):
    probe = ConcurrencyProbe(make_llm(clock=clock))
    client = make_client(llm=probe, max_concurrency=4)
    started = time.monotonic()
    body = classify(client, upload_id_for(client, "t.csv", many_tickets(16)))
    elapsed = time.monotonic() - started
    assert body["classified"] == 16
    assert [r["ticket_id"] for r in body["results"]] == [f"T{i:03d}" for i in range(16)]
    assert 2 <= probe.peak <= 4
    assert elapsed < 16 * probe.hold_s


def test_concurrency_limit_of_one(make_client, clock):
    probe = ConcurrencyProbe(make_llm(clock=clock), hold_s=0.01)
    client = make_client(llm=probe, max_concurrency=1)
    classify(client, upload_id_for(client, "t.csv", many_tickets(5)))
    assert probe.peak == 1


def test_rerun_only_attempts_unfinished_tickets(make_client, clock, tmp_path):
    llm = make_llm(LLMConfig(prompt_faults={"dark mode": ["malformed"] * 3}), clock)
    probe = ConcurrencyProbe(llm, hold_s=0)
    client = make_client(llm=probe)
    upload_id = upload_id_for(client)
    first = classify(client, upload_id)
    assert (first["classified"], first["failed"]) == (8, 1)
    calls_after_first = probe.calls

    second = classify(client, upload_id)
    assert probe.calls - calls_after_first == 1
    assert (second["classified"], second["failed"]) == (9, 0)
    rerun = {r["ticket_id"]: r for r in second["results"]}
    assert rerun["T-1004"]["attempts"] == 1 and rerun["T-1004"]["label"] == "feature_request"
    unchanged = {r["ticket_id"]: r for r in first["results"] if r["ticket_id"] != "T-1004"}
    assert all(rerun[k] == v for k, v in unchanged.items())
    assert client.get(f"/uploads/{upload_id}/classifications").json() == second

    third = classify(client, upload_id)
    assert probe.calls - calls_after_first == 1
    assert third == second
