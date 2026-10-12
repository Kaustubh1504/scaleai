"""48. Aggregations: plain Python vs pandas: reference solution."""

from __future__ import annotations

from collections import defaultdict


def total_by_annotator(rows: list[dict]) -> dict[str, int]:
    totals = defaultdict(int)
    for row in rows:
        totals[row["annotator"]] += row["amount_cents"]
    return dict(sorted(totals.items()))


def top_n_annotators(rows: list[dict], n: int) -> list[tuple[str, int]]:
    return sorted(total_by_annotator(rows).items(), key=lambda kv: (-kv[1], kv[0]))[:n]


def monthly_pivot(rows: list[dict]) -> dict[str, dict[str, int]]:
    months = sorted({row["date"][:7] for row in rows})
    pivot = {}
    for row in sorted(rows, key=lambda r: r["project"]):
        cells = pivot.setdefault(row["project"], dict.fromkeys(months, 0))
        cells[row["date"][:7]] += row["amount_cents"]
    return pivot


def _frame(rows: list[dict]):
    import pandas as pd

    df = pd.DataFrame(rows, columns=["date", "annotator", "project", "amount_cents"])
    df["month"] = df["date"].str[:7]
    return df


def total_by_annotator_pd(rows: list[dict]) -> dict[str, int]:
    totals = _frame(rows).groupby("annotator")["amount_cents"].sum()  # groupby sorts keys
    return {k: int(v) for k, v in totals.items()}


def top_n_annotators_pd(rows: list[dict], n: int) -> list[tuple[str, int]]:
    totals = _frame(rows).groupby("annotator", as_index=False)["amount_cents"].sum()
    top = totals.sort_values(["amount_cents", "annotator"], ascending=[False, True]).head(n)
    return [(a, int(c)) for a, c in zip(top["annotator"], top["amount_cents"])]


def monthly_pivot_pd(rows: list[dict]) -> dict[str, dict[str, int]]:
    if not rows:
        return {}
    table = _frame(rows).pivot_table(index="project", columns="month", values="amount_cents",
                                     aggfunc="sum", fill_value=0)
    return {p: {m: int(v) for m, v in row.items()} for p, row in table.iterrows()}


if __name__ == "__main__":
    from problem_api import load_rows

    rows = load_rows()
    print(total_by_annotator(rows))
    print(top_n_annotators(rows, 3))
    for project, months in monthly_pivot(rows).items():
        print(f"{project:<8}", months)
