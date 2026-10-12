import ast
import inspect
import json
import logging

import pytest

from problem_api import API_KEY, ENV, make_api

# What the original script printed for the sample data (finance diffs this).
EXPECTED_SUMMARY = """PAYOUT SUMMARY
ann_001  Ada Okafor              6 tasks  $0.90
ann_002  Bo Lindqvist            5 tasks  $0.50
ann_004  Di Moreau               3 tasks  $0.45
ann_007  Gus Albright            1 tasks  $0.38
ann_005  Eli Navarro             3 tasks  $0.15
TOTAL $2.38 across 5 annotators"""


def ann(aid, level="junior", active=True, name=None):
    return {"id": aid, "name": name or aid.title(), "level": level, "active": active}


def sub(sid, aid, task_type="bbox", status="accepted"):
    return {"id": sid, "annotator_id": aid, "task_type": task_type, "status": status}


def test_load_config(sol):
    """load_config reads required vars, applies defaults and parses optional ones"""
    cfg = sol.load_config(dict(ENV))
    assert (cfg.base_url, cfg.api_key, cfg.timeout_s, cfg.per_page) == (ENV["PAYOUT_API_URL"], API_KEY, 10.0, 50)
    cfg = sol.load_config({**ENV, "PAYOUT_TIMEOUT_S": "2.5", "PAYOUT_PER_PAGE": "3"})
    assert (cfg.timeout_s, cfg.per_page) == (2.5, 3)


def test_load_config_errors(sol):
    """load_config raises ConfigError naming the missing or invalid variable"""
    cases = [
        ({"PAYOUT_API_URL": ENV["PAYOUT_API_URL"]}, "PAYOUT_API_KEY"),
        ({**ENV, "PAYOUT_API_URL": "  "}, "PAYOUT_API_URL"),
        ({**ENV, "PAYOUT_PER_PAGE": "500"}, "PAYOUT_PER_PAGE"),
        ({**ENV, "PAYOUT_PER_PAGE": "ten"}, "PAYOUT_PER_PAGE"),
        ({**ENV, "PAYOUT_TIMEOUT_S": "0"}, "PAYOUT_TIMEOUT_S"),
    ]
    for env, name in cases:
        with pytest.raises(sol.ConfigError) as exc:
            sol.load_config(env)
        assert name in str(exc.value), f"ConfigError for {env} should mention {name}: {exc.value}"


def test_paginate_all_pages(sol, caplog):
    """ApiClient.paginate yields every item across pages with auth + per_page, logging DEBUG per page"""
    caplog.set_level(logging.DEBUG)
    api = make_api()
    cfg = sol.load_config({**ENV, "PAYOUT_PER_PAGE": "10"})
    items = list(sol.ApiClient(api.client(), cfg).paginate("/v1/submissions"))
    assert [s["id"] for s in items] == [s["id"] for s in api.submissions], "items missing or out of order"
    calls = api.calls("GET", "/v1/submissions")
    assert [c.params.get("page") for c in calls] == ["1", "2", "3", "4", "5"], "47 items at 10/page = 5 pages"
    assert all(c.params.get("per_page") == "10" for c in calls), "send per_page from the config"
    assert all(c.header("authorization") == f"Bearer {API_KEY}" for c in calls)
    debug = [r for r in caplog.records if r.name == sol.__name__ and r.levelno == logging.DEBUG]
    assert len(debug) >= 5, "log one DEBUG message per page via logging.getLogger(__name__)"


def test_paginate_errors(sol):
    """paginate raises ApiError(status, path) on a non-2xx and on a non-JSON body"""
    api = make_api()
    api.script("GET /v1/annotators", [503])
    with pytest.raises(sol.ApiError) as exc:
        list(sol.ApiClient(api.client(), sol.load_config(ENV)).paginate("/v1/annotators"))
    assert (exc.value.status, exc.value.path) == (503, "/v1/annotators")

    api.script("GET /v1/annotators", ["malformed"])
    with pytest.raises(sol.ApiError):
        list(sol.ApiClient(api.client(), sol.load_config(ENV)).paginate("/v1/annotators"))


def test_compute_payouts_rules(sol):
    """compute_payouts: accepted only, active only, rates, +25% senior bonus rounded half up, sorted"""
    annotators = [ann("a1", "senior"), ann("a2"), ann("a3", active=False), ann("a4")]
    submissions = [
        sub("s1", "a1", "transcribe"),                # 30 -> 37.5 -> 38 (half up)
        sub("s2", "a2", "bbox"), sub("s3", "a2", "classify"), sub("s4", "a2", "transcribe"),  # 47
        sub("s5", "a2", "bbox", status="rejected"),
        sub("s6", "a2", "bbox", status="pending"),
        sub("s7", "a3", "transcribe"),                # inactive
        sub("s8", "ghost", "transcribe"),             # unknown annotator
        sub("s9", "a4", "classify", status="rejected"),  # a4 has nothing paid -> absent
    ]
    got = sol.compute_payouts(annotators, submissions)
    assert got == [sol.Payout("a2", "A2", 3, 47), sol.Payout("a1", "A1", 1, 38)]


def test_compute_payouts_ties_and_unknown_type(sol, caplog):
    """Ties sort by annotator id; an unknown task_type is skipped with a WARNING naming the submission"""
    caplog.set_level(logging.DEBUG)
    annotators = [ann("b2"), ann("b1")]
    submissions = [sub("s1", "b2", "bbox"), sub("s2", "b1", "bbox"), sub("s3", "b1", "polygon")]
    got = sol.compute_payouts(annotators, submissions)
    assert [(p.annotator_id, p.tasks, p.amount_cents) for p in got] == [("b1", 1, 12), ("b2", 1, 12)]
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING and r.name == sol.__name__]
    assert any("s3" in r.getMessage() for r in warnings), "log a WARNING that names the skipped submission"


def test_main_matches_old_report(sol, capsys):
    """main() returns 0 and prints exactly the old script's report (no debug noise)"""
    api = make_api()
    code = sol.main([], dict(ENV), api.client())
    out = capsys.readouterr().out
    assert code == 0
    assert out == EXPECTED_SUMMARY + "\n", f"report changed or diagnostics leaked into stdout:\n{out}"
    assert sol.format_summary(sol.compute_payouts(api.annotators, api.submissions)) == EXPECTED_SUMMARY


def test_main_json(sol, capsys):
    """main(['--json']) prints the payouts as a JSON array"""
    code = sol.main(["--json"], dict(ENV), make_api().client())
    rows = json.loads(capsys.readouterr().out)
    assert code == 0
    assert rows[0] == {"annotator_id": "ann_001", "name": "Ada Okafor", "tasks": 6, "amount_cents": 90}
    assert [r["annotator_id"] for r in rows] == ["ann_001", "ann_002", "ann_004", "ann_007", "ann_005"]


def test_main_bad_config(sol, capsys, caplog):
    """main() with bad config logs an ERROR, prints nothing, makes no requests and returns 2"""
    api = make_api()
    code = sol.main([], {"PAYOUT_API_URL": ENV["PAYOUT_API_URL"]}, api.client())
    assert code == 2
    assert capsys.readouterr().out == ""
    assert api.log == [], "don't call the API with a broken config"
    assert any(r.levelno == logging.ERROR for r in caplog.records), "log the config problem at ERROR"


def test_main_api_error(sol, capsys, caplog):
    """main() on a 503 logs an ERROR, prints nothing and returns 1 (no sys.exit)"""
    api = make_api()
    api.script("GET /v1/submissions", [503])
    code = sol.main([], dict(ENV), api.client())
    assert code == 1
    assert capsys.readouterr().out == "", "no partial report on failure"
    assert any(r.levelno == logging.ERROR and r.name == sol.__name__ for r in caplog.records)


def test_code_hygiene(sol):
    """No bare except, no sys.exit, no print outside main, no hard-coded key or URL"""
    source = inspect.getsource(sol)
    assert API_KEY not in source, "the API key is hard-coded in your file"
    assert ENV["PAYOUT_API_URL"] not in source, "the base URL is hard-coded in your file"
    tree = ast.parse(source)
    problems = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            problems.append(f"line {node.lineno}: bare except")
        if isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Attribute) and f.attr == "exit" and getattr(f.value, "id", "") == "sys":
                if not _in_main_guard(tree, node):
                    problems.append(f"line {node.lineno}: sys.exit")
            if isinstance(f, ast.Name) and f.id in ("exit", "quit"):
                problems.append(f"line {node.lineno}: {f.id}()")
    for fn in ast.walk(tree):
        if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)) and fn.name != "main":
            for node in ast.walk(fn):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print":
                    problems.append(f"line {node.lineno}: print() in {fn.name}(); use logging")
    assert not problems, "; ".join(problems)


def _in_main_guard(tree, target):
    for node in tree.body:
        if isinstance(node, ast.If) and "__main__" in ast.unparse(node.test):
            if any(n is target for n in ast.walk(node)):
                return True
    return False
