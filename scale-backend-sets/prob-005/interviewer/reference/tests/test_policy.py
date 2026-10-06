import random

import httpx
import pytest

from dispatcher.policy import Backoff, parse_retry_after, retryable_error, retryable_status


@pytest.mark.parametrize("code, expected", [
    (408, True), (429, True), (500, True), (503, True), (599, True),
    (301, False), (400, False), (401, False), (404, False), (410, False), (422, False),
])
def test_retryable_status(code, expected):
    assert retryable_status(code) is expected


def test_retryable_errors():
    request = httpx.Request("POST", "http://x")
    assert retryable_error(httpx.ConnectError("reset", request=request))
    assert retryable_error(httpx.ReadTimeout("slow", request=request))
    assert retryable_error(httpx.ConnectTimeout("slow", request=request))
    assert not retryable_error(httpx.RemoteProtocolError("garbage", request=request))
    assert not retryable_error(httpx.UnsupportedProtocol("ftp"))


@pytest.mark.parametrize("value, expected", [("30", 30.0), (" 0 ", 0.0), ("900", 900.0), ("-1", None),
                                             ("1.5", None), ("Wed, 21 Oct 2015 07:28:00 GMT", None), ("", None)])
def test_parse_retry_after(value, expected):
    assert parse_retry_after(httpx.Response(429, headers={"Retry-After": value})) == expected


def test_parse_retry_after_missing():
    assert parse_retry_after(httpx.Response(429)) is None


@pytest.mark.parametrize("attempt, ceiling", [(1, 10), (2, 20), (3, 40), (4, 80), (5, 160), (6, 300), (50, 300)])
def test_backoff_bounds(attempt, ceiling):
    backoff = Backoff(random.Random(attempt))
    delays = [backoff.delay(attempt) for _ in range(200)]
    assert all(ceiling / 2 <= d <= ceiling for d in delays)
    assert len(set(delays)) > 100
