import pytest

from problem_api import make_api

T = 1_700_000_000.0


def path(i):
    return f"/v1/annotations/ann_{i:03d}"


def run(sol, api, clock, n):
    tc = sol.ThrottledClient(api.client(), clock)
    return [tc.get(path(i)) for i in range(1, n + 1)]


def test_fifty_requests_no_429s(sol, clock):
    """50 requests at 5 req/s: every one succeeds and the server never sends a 429"""
    api = make_api(clock)
    responses = run(sol, api, clock, 50)
    statuses = [r.status_code for r in responses]
    assert api.limiter.rejected == 0, f"the server rejected {api.limiter.rejected} requests"
    assert statuses == [200] * 50, f"statuses: {statuses}"
    assert [r.json()["id"] for r in responses] == [f"ann_{i:03d}" for i in range(1, 51)]


def test_total_sleep_is_minimal(sol, clock):
    """50 requests from a window boundary sleep exactly 9 x 1.0 s, no more"""
    api = make_api(clock)
    run(sol, api, clock, 50)
    assert len(clock.sleeps) == 9, f"10 windows of 5 need 9 waits, got {len(clock.sleeps)}: {clock.sleeps}"
    assert clock.total_slept == pytest.approx(9.0, abs=1e-6), \
        f"theoretical minimum is 9.0 s, you slept {clock.total_slept}"


def test_sleeps_only_until_reset(sol, clock):
    """Starting 0.4 s into a window, the first wait is 0.6 s (until Reset), total 8.6 s"""
    clock.set(T + 0.4)
    api = make_api(clock)
    run(sol, api, clock, 50)
    assert api.limiter.rejected == 0
    assert clock.sleeps[0] == pytest.approx(0.6, abs=1e-6), \
        f"sleep until X-RateLimit-Reset, not a fixed 1 s: first sleep was {clock.sleeps[0]}"
    assert clock.total_slept == pytest.approx(8.6, abs=1e-6)


def test_no_sleep_while_budget_remains(sol, clock):
    """The first 5 requests in a window go out without any sleep"""
    api = make_api(clock)
    run(sol, api, clock, 5)
    assert clock.sleeps == [], f"Remaining never hit 0 before a request, so no sleep: {clock.sleeps}"


def test_slow_traffic_never_sleeps(sol, clock):
    """With 0.3 s latency per request the window never runs out, so nothing sleeps"""
    api = make_api(clock, latency_s=0.3)
    run(sol, api, clock, 20)
    assert api.limiter.rejected == 0
    assert clock.sleeps == [], f"don't pace requests when the headers say there's room: {clock.sleeps}"


def test_no_sleep_when_reset_already_passed(sol, clock):
    """If time already passed Reset since the last response, the next request goes out at once"""
    api = make_api(clock)
    tc = sol.ThrottledClient(api.client(), clock)
    for i in range(1, 6):
        tc.get(path(i))
    clock.advance(2.5)  # we were busy elsewhere
    resp = tc.get(path(6))
    assert resp.status_code == 200
    assert clock.sleeps == [], f"Reset is in the past, so no sleep (and never a negative one): {clock.sleeps}"


def test_passes_through_requests_and_responses(sol, clock):
    """request() forwards method and kwargs and returns the response unchanged (even a 404)"""
    api = make_api(clock)
    tc = sol.ThrottledClient(api.client(), clock)
    resp = tc.request("GET", "/v1/annotations/ann_999", params={"expand": "task"}, headers={"X-Trace": "abc"})
    assert resp.status_code == 404, "the wrapper must not raise or swallow error responses"
    c = api.log[-1]
    assert c.params == {"expand": "task"}, "params= must be forwarded"
    assert c.header("x-trace") == "abc", "headers= must be forwarded"


def test_bucket_starts_full(sol, clock):
    """A new TokenBucket(burst=3) hands out 3 tokens without sleeping"""
    bucket = sol.TokenBucket(rate_per_s=2, burst=3, clock=clock)
    for _ in range(3):
        bucket.acquire()
    assert clock.sleeps == [], f"the bucket starts full: {clock.sleeps}"


def test_bucket_waits_one_over_rate_when_empty(sol, clock):
    """Once empty, each acquire sleeps 1 / rate_per_s (0.5 s at 2/s, 2 s at 0.5/s)"""
    bucket = sol.TokenBucket(rate_per_s=2, burst=3, clock=clock)
    for _ in range(5):
        bucket.acquire()
    assert clock.sleeps == pytest.approx([0.5, 0.5], abs=1e-6)

    clock.sleeps.clear()
    slow = sol.TokenBucket(rate_per_s=0.5, burst=1, clock=clock)
    slow.acquire()
    slow.acquire()
    assert clock.sleeps == pytest.approx([2.0], abs=1e-6)


def test_bucket_fractional_tokens(sol, clock):
    """Partial refills count: with 0.5 tokens left at 4/s, acquire sleeps only 0.125 s"""
    bucket = sol.TokenBucket(rate_per_s=4, burst=2, clock=clock)
    bucket.acquire()
    bucket.acquire()
    clock.advance(0.125)  # refills 0.5 tokens
    bucket.acquire()
    assert clock.sleeps == pytest.approx([0.125], abs=1e-6), \
        f"deficit is 0.5 tokens = 0.125 s at 4/s, slept {clock.sleeps}"
    clock.advance(0.1)    # refills 0.4 tokens
    bucket.acquire()
    assert clock.sleeps == pytest.approx([0.125, 0.15], abs=1e-6)


def test_bucket_refill_capped_at_burst(sol, clock):
    """An idle bucket refills to burst and no further"""
    bucket = sol.TokenBucket(rate_per_s=1, burst=3, clock=clock)
    for _ in range(3):
        bucket.acquire()
    clock.advance(100)
    for _ in range(3):
        bucket.acquire()
    assert clock.sleeps == [], "3 tokens should be available after a long idle"
    bucket.acquire()
    assert clock.sleeps == pytest.approx([1.0], abs=1e-6), "the bucket holds at most burst=3 tokens"


def test_bucket_steady_rate(sol, clock):
    """20 acquires at rate 5, burst 5 take 3.0 s of sleep: 5 free, then 15 at 0.2 s"""
    bucket = sol.TokenBucket(rate_per_s=5, burst=5, clock=clock)
    for _ in range(20):
        bucket.acquire()
    assert len(clock.sleeps) == 15
    assert clock.total_slept == pytest.approx(3.0, abs=1e-6)
