import pytest

from problem_api import load_rows

SMALL = [
    {"date": "2024-02-09", "annotator": "a", "project": "cars", "amount_cents": 150},
    {"date": "2024-01-05", "annotator": "a", "project": "cars", "amount_cents": 100},
    {"date": "2024-02-01", "annotator": "b", "project": "docs", "amount_cents": 250},
    {"date": "2024-03-30", "annotator": "c", "project": "audio", "amount_cents": 40},
]


def test_total_by_annotator(sol):
    """total_by_annotator sums cents per annotator, keys ascending"""
    got = sol.total_by_annotator(SMALL)
    assert got == {"a": 250, "b": 250, "c": 40}
    assert list(got) == ["a", "b", "c"], "keys must be in ascending order"


def test_top_n_ties(sol):
    """top_n_annotators orders by total desc, ties by annotator asc"""
    assert sol.top_n_annotators(SMALL, 2) == [("a", 250), ("b", 250)]
    assert sol.top_n_annotators(SMALL, 10) == [("a", 250), ("b", 250), ("c", 40)]


def test_pivot_fills_zeros(sol):
    """monthly_pivot gives every project every month (ascending), 0 where empty"""
    got = sol.monthly_pivot(SMALL)
    months = {"2024-01": 0, "2024-02": 0, "2024-03": 0}
    assert got == {
        "audio": {**months, "2024-03": 40},
        "cars": {**months, "2024-01": 100, "2024-02": 150},
        "docs": {**months, "2024-02": 250},
    }
    assert list(got) == ["audio", "cars", "docs"], "projects must be ascending"
    assert list(got["cars"]) == ["2024-01", "2024-02", "2024-03"], "months must be ascending"


def test_empty_input(sol):
    """Empty input gives {}, [] and {}"""
    assert sol.total_by_annotator([]) == {}
    assert sol.top_n_annotators([], 3) == []
    assert sol.monthly_pivot([]) == {}


def test_sample_file(sol):
    """On data/payouts.csv the totals add up to the ledger and the pivot matches"""
    rows = load_rows()
    totals = sol.total_by_annotator(rows)
    assert sum(totals.values()) == sum(r["amount_cents"] for r in rows), "every cent must be counted once"
    assert totals == {"ann_ada": 1875, "ann_bo": 6800, "ann_cy": 2950, "ann_di": 4295, "ann_eli": 5120}
    assert sol.top_n_annotators(rows, 2) == [("ann_bo", 6800), ("ann_eli", 5120)]
    pivot = sol.monthly_pivot(rows)
    assert sum(sum(m.values()) for m in pivot.values()) == sum(totals.values())
    assert all(list(m) == ["2024-01", "2024-02", "2024-03"] for m in pivot.values())


def test_no_top_level_pandas_import(sol):
    """pandas is imported only inside the _pd functions, never at module level"""
    import ast
    import inspect

    tree = ast.parse(inspect.getsource(sol))
    for node in tree.body:
        names = []
        if isinstance(node, ast.Import):
            names = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [node.module or ""]
        assert not any(n.split(".")[0] == "pandas" for n in names), \
            f"line {node.lineno}: a module-level pandas import breaks your file wherever pandas is missing"


def test_pandas_versions_match(sol):
    """(optional, needs pandas) the _pd versions return the same results"""
    pytest.importorskip("pandas")
    for rows in (SMALL, load_rows()):
        assert sol.total_by_annotator_pd(rows) == sol.total_by_annotator(rows)
        assert sol.top_n_annotators_pd(rows, 3) == sol.top_n_annotators(rows, 3)
        assert sol.monthly_pivot_pd(rows) == sol.monthly_pivot(rows)


def test_pandas_returns_plain_ints(sol):
    """(optional, needs pandas) the _pd versions return plain ints, not numpy ints"""
    pytest.importorskip("pandas")
    assert type(next(iter(sol.total_by_annotator_pd(SMALL).values()))) is int
    assert type(sol.top_n_annotators_pd(SMALL, 1)[0][1]) is int
