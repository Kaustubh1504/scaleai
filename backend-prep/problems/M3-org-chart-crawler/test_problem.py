import json
import os
from pathlib import Path

import pytest

from problem_api import CLIENT_ID, CLIENT_SECRET, make_api, person

SAMPLE_ORDER = ["org_root", "org_eng", "org_ops", "org_platform", "org_ml", "org_support", "org_legal",
                "org_research"]
SAMPLE_HEADCOUNT = {"org_root": 46, "org_eng": 16, "org_ops": 28, "org_platform": 9, "org_ml": 14,
                    "org_support": 25, "org_legal": 2, "org_research": 14}


def client_for(sol, api, secret=CLIENT_SECRET):
    return sol.OrgClient(api.client(), CLIENT_ID, secret, clock=api.clock)


def crawl(sol, api, root="org_root", **kw):
    return sol.crawl_org(client_for(sol, api), root, **kw)


def graph(edges: dict[str, list[str]]) -> dict[str, dict]:
    return {org: {"name": org.upper(), "children": kids} for org, kids in edges.items()}


def people(*ns):
    return [person(n) for n in ns]


def ok_org_fetches(api):
    return [c.path for c in api.log if c.status == 200 and c.path.startswith("/v1/orgs/")
            and not c.path.endswith("/members")]


def v1(api):
    return [c for c in api.log if c.path.startswith("/v1/")]


class Crash(BaseException):
    """Simulates the process being killed (not an Exception, so nobody swallows it)."""


def crash(call):
    raise Crash("killed")


# ------------------------------------------------------------------ part 1


def test_part1_sample_org_chart(sol):
    """Sample chart: BFS order, headcount per subtree and the dangling org"""
    result = crawl(sol, make_api())
    assert result.order == SAMPLE_ORDER
    assert result.headcount == SAMPLE_HEADCOUNT
    assert result.dangling == ["org_legacy"]
    assert result.inaccessible == []


def test_part1_member_pagination(sol):
    """Follows every members page (first without a cursor, limit within 1..50)"""
    api = make_api(graph({"r": ["a"], "a": []}), {"r": people(*range(1, 121)), "a": people(200)})
    result = crawl(sol, api, "r")
    assert result.headcount == {"r": 121, "a": 1}
    pages = api.calls("GET", "/v1/orgs/r/members")
    assert len(pages) >= 3, "120 members need several pages"
    assert "cursor" not in pages[0].params
    assert not [c for c in api.log if c.status == 400], "a request was rejected (bad limit or cursor?)"


def test_part1_each_org_requested_once(sol):
    """Cycles and orgs with several parents: each org and each members page is requested once"""
    api = make_api()
    crawl(sol, api)
    fetched = [c.path for c in api.log if c.method == "GET" and c.path.startswith("/v1/orgs/")]
    assert len(fetched) == len(set(fetched)), "some org or members page was requested twice"
    assert sorted(ok_org_fetches(api)) == sorted(f"/v1/orgs/{o}" for o in SAMPLE_ORDER)


def test_part1_distinct_people_and_cycles(sol):
    """A person in several orgs counts once; orgs in a cycle share a subtree"""
    orgs = graph({"r": ["a"], "a": ["b"], "b": ["c"], "c": ["a", "d"], "d": []})
    members = {"r": people(1), "a": people(2, 3), "b": people(3, 4), "c": people(2, 5), "d": people(6, 7)}
    result = crawl(sol, make_api(orgs, members), "r")
    assert result.headcount == {"r": 7, "a": 6, "b": 6, "c": 6, "d": 2}


def test_part1_bfs_order(sol):
    """Orgs are visited level by level, children in listed order"""
    orgs = graph({"r": ["a", "b"], "a": ["c"], "b": ["d", "a"], "c": ["e"], "d": [], "e": []})
    result = crawl(sol, make_api(orgs, {}), "r")
    assert result.order == ["r", "a", "b", "c", "d", "e"]
    assert result.headcount == {o: 0 for o in result.order}, "orgs with no members count 0"


def test_part1_dangling_refs(sol):
    """404 children are recorded once (sorted) and the crawl carries on; a missing root raises ApiError(404)"""
    orgs = graph({"r": ["zz_gone", "a", "b"], "a": ["aa_gone"], "b": ["zz_gone"]})
    result = crawl(sol, make_api(orgs, {"a": people(1), "b": people(2)}), "r")
    assert result.dangling == ["aa_gone", "zz_gone"]
    assert result.order == ["r", "a", "b"] and result.headcount["r"] == 2
    with pytest.raises(sol.ApiError) as exc:
        crawl(sol, make_api(orgs, {}), "nope")
    assert (exc.value.status, exc.value.path) == (404, "/v1/orgs/nope")


def test_part1_other_errors_raise(sol):
    """A 500 on a members page raises ApiError(500) with that path"""
    api = make_api()
    api.script("GET /v1/orgs/org_ops/members", [500])
    with pytest.raises(sol.ApiError) as exc:
        crawl(sol, api)
    assert (exc.value.status, exc.value.path) == (500, "/v1/orgs/org_ops/members")


# ------------------------------------------------------------------ part 2


def test_part2_bearer_token_on_every_request(sol):
    """Gets one token with the credentials and sends it as Bearer on every /v1 request"""
    api = make_api(auth=True)
    assert crawl(sol, api).headcount == SAMPLE_HEADCOUNT
    tokens = api.calls("POST", "/oauth/token")
    assert len(tokens) == 1 and tokens[0].json() == {"client_id": CLIENT_ID, "client_secret": CLIENT_SECRET}
    assert all(c.header("authorization") == "Bearer tok_00001" for c in v1(api))


def test_part2_proactive_refresh_avoids_401s(sol, clock):
    """With 20 s tokens and 1 s per request, refreshing 5 s early means the crawl never sees a 401"""
    api = make_api(auth=True, token_ttl_s=20, latency_s=1.0, clock=clock)
    result = crawl(sol, api)
    assert result.headcount == SAMPLE_HEADCOUNT
    assert api.tokens.issued >= 2, "the crawl outlives one token"
    assert [c.path for c in v1(api) if c.status == 401] == [], "refresh before expiry (5 s margin)"


def test_part2_revoked_token_retried_once(sol):
    """An unexpected 401 triggers one refresh and one resend; the crawl completes"""
    api = make_api(auth=True)
    api.script("GET /v1/orgs/org_ops", [401])
    result = crawl(sol, api)
    assert result.headcount == SAMPLE_HEADCOUNT
    assert api.tokens.issued == 2
    sends = api.calls("GET", "/v1/orgs/org_ops")
    assert [c.status for c in sends] == [401, 200]
    assert sends[1].header("authorization") == "Bearer tok_00002", "resend with the new token"


def test_part2_second_401_raises_auth_error(sol):
    """Two 401s in a row for the same request raise AuthError"""
    api = make_api(auth=True)
    api.script("GET /v1/orgs/org_eng", [401, 401])
    with pytest.raises(sol.AuthError):
        crawl(sol, api)
    assert len(api.calls("GET", "/v1/orgs/org_eng")) == 2


def test_part2_bad_credentials(sol):
    """A rejected token request raises AuthError (an ApiError)"""
    api = make_api(auth=True)
    with pytest.raises(sol.AuthError) as exc:
        sol.crawl_org(client_for(sol, api, secret="wrong"), "org_root")
    assert isinstance(exc.value, sol.ApiError) and exc.value.status == 401


def test_part2_forbidden_orgs_are_inaccessible(sol):
    """403 orgs are listed as inaccessible and not crawled through; the rest of the crawl continues"""
    api = make_api(auth=True, forbidden={"org_ops", "org_research"})
    result = crawl(sol, api)
    assert result.inaccessible == ["org_ops", "org_research"]
    assert result.order == ["org_root", "org_eng", "org_platform", "org_ml"]
    assert result.headcount == {"org_root": 16, "org_eng": 14, "org_platform": 9, "org_ml": 3}
    assert result.dangling == ["org_legacy"]
    assert not api.calls("GET", "/v1/orgs/org_support"), "children of an inaccessible org are not reachable"


# ------------------------------------------------------------------ part 3


def test_part3_never_triggers_a_429(sol, clock):
    """Waits for X-RateLimit-Reset whenever Remaining hits 0: zero 429s, correct result"""
    api = make_api(auth=True, rate_limit=3, latency_s=0.1, clock=clock)
    result = crawl(sol, api)
    assert result.headcount == SAMPLE_HEADCOUNT
    assert api.limiter.rejected == 0, "the client triggered 429s"
    assert clock.sleeps and all(0 < s <= 1.0 for s in clock.sleeps)


def test_part3_waits_exactly_until_reset(sol, clock):
    """Sleeps reset - now, and only when Remaining is 0"""
    api = make_api(rate_limit=2, clock=clock)
    crawl(sol, api)
    n = len(v1(api))
    assert api.limiter.rejected == 0
    assert clock.sleeps[0] == pytest.approx(1.0), "two requests at t0, then wait the full window"
    assert len(clock.sleeps) == (n - 1) // 2, "sleep once per full window, never otherwise"


def test_part3_unexpected_429_is_retried(sol, clock):
    """A 429 anyway: sleep Retry-After and resend; the 5th 429 in a row raises ApiError(429)"""
    api = make_api(clock=clock)
    api.script("GET /v1/orgs/org_eng", ["429:2"])
    assert crawl(sol, api).headcount == SAMPLE_HEADCOUNT
    assert clock.sleeps == [2.0]
    api = make_api(clock=clock)
    api.script("GET /v1/orgs/org_eng", ["429:1"] * 6)
    with pytest.raises(sol.ApiError) as exc:
        crawl(sol, api)
    assert exc.value.status == 429 and len(api.calls("GET", "/v1/orgs/org_eng")) == 5


def test_part3_resume_after_crash(sol, tmp_path):
    """After a crash the checkpoint is valid JSON; the re-run skips finished orgs and gives the same result"""
    ckpt = tmp_path / "crawl.json"
    api = make_api(auth=True)
    api.script("GET /v1/orgs/org_ml/members", [crash])
    with pytest.raises(Crash):
        crawl(sol, api, checkpoint_path=ckpt)
    json.loads(ckpt.read_text())
    api2 = make_api(auth=True)
    result = crawl(sol, api2, checkpoint_path=ckpt)
    assert (result.order, result.headcount, result.dangling) == (SAMPLE_ORDER, SAMPLE_HEADCOUNT, ["org_legacy"])
    refetched = {c.path for c in v1(api2)}
    for done in ("org_root", "org_eng", "org_ops", "org_platform", "org_legacy"):
        assert f"/v1/orgs/{done}" not in refetched, f"{done} was finished before the crash"
    assert "/v1/orgs/org_ml" in refetched, "the half-done org is fetched again"
    assert not ckpt.exists(), "delete the checkpoint when the crawl completes"


def test_part3_resume_keeps_dangling_and_inaccessible(sol, tmp_path):
    """Dangling and inaccessible orgs found before a crash survive the resume without new requests"""
    ckpt = tmp_path / "crawl.json"
    api = make_api(auth=True, forbidden={"org_legal"})
    api.script("GET /v1/orgs/org_research/members", [crash])
    with pytest.raises(Crash):
        crawl(sol, api, checkpoint_path=ckpt)
    api2 = make_api(auth=True, forbidden={"org_legal"})
    result = crawl(sol, api2, checkpoint_path=ckpt)
    assert result.dangling == ["org_legacy"] and result.inaccessible == ["org_legal"]
    assert result.headcount["org_root"] == 44 and "org_legal" not in result.order
    assert sorted({c.path for c in v1(api2)}) == ["/v1/orgs/org_research", "/v1/orgs/org_research/members"]


def test_part3_checkpoint_written_atomically(sol, tmp_path, monkeypatch):
    """The checkpoint is replaced atomically after every finished org and nothing is left behind"""
    ckpt = tmp_path / "state" / "crawl.json"
    ckpt.parent.mkdir()
    real_replace = os.replace
    targets = []

    def recording(src, dst, *a, **kw):
        targets.append((Path(src).parent, Path(dst)))
        return real_replace(src, dst, *a, **kw)

    monkeypatch.setattr(os, "replace", recording)
    crawl(sol, make_api(), checkpoint_path=ckpt)
    to_ckpt = [src_dir for src_dir, dst in targets if dst == ckpt]
    assert len(to_ckpt) >= 9, "write after each finished org (8 crawled + 1 dangling)"
    assert all(d == ckpt.parent for d in to_ckpt), "the temporary file must live next to the checkpoint"
    assert list(ckpt.parent.iterdir()) == [], "checkpoint deleted and no temp files left"
