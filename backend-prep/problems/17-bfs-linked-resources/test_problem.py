from collections import Counter

import pytest

from problem_api import make_api, org

ALL_TEAMS = ["t_backend", "t_exec", "t_frontend", "t_infra", "t_ml", "t_ops", "t_research", "t_support"]
MISSING = ["org_ghost", "org_vendor_gone"]


def graph(*orgs):
    return {o["id"]: o for o in orgs}


def node(org_id, children=(), parent=None):
    return org(org_id, parent, list(children), [f"t_{org_id}"])


def test_full_crawl(sol):
    """Crawling org_acme returns 7 orgs, 8 sorted unique teams and 2 missing orgs"""
    api = make_api()
    result = sol.collect_teams(api.client(), "org_acme")
    assert result == {"orgs_visited": 7, "team_ids": ALL_TEAMS, "missing_orgs": MISSING}


def test_each_org_fetched_once(sol):
    """Duplicates, a shared child and a cycle still mean one request per org id (9 in total)"""
    api = make_api()
    sol.collect_teams(api.client(), "org_acme")
    per_path = Counter(c.path for c in api.log)
    dupes = {p: n for p, n in per_path.items() if n > 1}
    assert not dupes, f"fetched more than once: {dupes}"
    assert len(api.log) == 9, f"expected 9 requests (7 orgs + 2 404s), made {len(api.log)}"


def test_does_not_follow_parent(sol):
    """The crawl goes down through children only: org_holding and its other child are never requested"""
    api = make_api()
    sol.collect_teams(api.client(), "org_acme")
    paths = {c.path for c in api.log}
    assert "/v1/orgs/org_holding" not in paths, "don't follow `parent`"
    assert "/v1/orgs/org_other" not in paths


def test_cycle_from_mid_tree(sol):
    """Starting at org_ml, whose child is its ancestor org_acme, the crawl terminates and finds everything"""
    api = make_api()
    result = sol.collect_teams(api.client(), "org_ml")
    assert result == {"orgs_visited": 7, "team_ids": ALL_TEAMS, "missing_orgs": MISSING}
    assert len(api.log) == 9


def test_dangling_child_is_reported(sol):
    """A child that 404s goes in missing_orgs, and its siblings are still crawled"""
    api = make_api(graph(node("root", ["gone", "a"]), node("a", ["gone"])))
    result = sol.collect_teams(api.client(), "root")
    assert result == {"orgs_visited": 2, "team_ids": ["t_a", "t_root"], "missing_orgs": ["gone"]}
    assert len(api.calls("GET", "/v1/orgs/gone")) == 1, "a 404 is an answer too: don't request it again"


def test_max_depth_zero(sol):
    """max_depth=0 fetches only the root"""
    api = make_api()
    result = sol.collect_teams(api.client(), "org_acme", max_depth=0)
    assert result == {"orgs_visited": 1, "team_ids": ["t_exec"], "missing_orgs": []}
    assert len(api.log) == 1, "children are at depth 1: don't even request them"


def test_max_depth_one(sol):
    """max_depth=1 fetches the root and its children, nothing deeper"""
    api = make_api()
    result = sol.collect_teams(api.client(), "org_acme", max_depth=1)
    assert result == {"orgs_visited": 3, "team_ids": ["t_backend", "t_exec", "t_frontend", "t_ops"],
                      "missing_orgs": ["org_ghost"]}
    assert len(api.log) == 4, f"expected 4 requests (acme, eng, ops, ghost), made {len(api.log)}"


def test_depth_is_shortest_distance(sol):
    """Depth is the shortest path: root->[a, b], a->[b], b->[c] with max_depth=2 reaches c"""
    api = make_api(graph(node("root", ["a", "b"]), node("a", ["b"]), node("b", ["c"]), node("c")))
    result = sol.collect_teams(api.client(), "root", max_depth=2)
    assert result["team_ids"] == ["t_a", "t_b", "t_c", "t_root"], \
        "b is at depth 1 (root->b), so c is at depth 2; a depth-first walk reaches b at depth 2 and misses c"
    assert result["orgs_visited"] == 4


def test_root_not_found_raises(sol):
    """A 404 for the root raises ApiError(404) with the root's path"""
    api = make_api()
    with pytest.raises(sol.ApiError) as exc:
        sol.collect_teams(api.client(), "org_nope")
    assert exc.value.status == 404
    assert exc.value.path == "/v1/orgs/org_nope"


def test_server_error_raises(sol):
    """A 500 for a child raises ApiError(500) instead of being treated as missing"""
    api = make_api()
    api.script("GET /v1/orgs/org_ops", [500])
    with pytest.raises(sol.ApiError) as exc:
        sol.collect_teams(api.client(), "org_acme")
    assert exc.value.status == 500
    assert exc.value.path == "/v1/orgs/org_ops"


def test_leaf_root(sol):
    """A root with no children returns just its own teams after one request"""
    api = make_api()
    result = sol.collect_teams(api.client(), "org_research")
    assert result == {"orgs_visited": 1, "team_ids": ["t_research"], "missing_orgs": []}
    assert len(api.log) == 1
