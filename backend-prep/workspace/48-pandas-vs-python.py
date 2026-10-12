"""48. Aggregations: plain Python vs pandas

Template: imports, constants, exceptions and signatures are here.
Fill in every `raise NotImplementedError` (add your own helpers as needed)."""

from __future__ import annotations
from collections import defaultdict


def total_by_annotator(rows: list[dict]) -> dict[str, int]:
    raise NotImplementedError


def top_n_annotators(rows: list[dict], n: int) -> list[tuple[str, int]]:
    raise NotImplementedError


def monthly_pivot(rows: list[dict]) -> dict[str, dict[str, int]]:
    raise NotImplementedError


def total_by_annotator_pd(rows: list[dict]) -> dict[str, int]:
    raise NotImplementedError


def top_n_annotators_pd(rows: list[dict], n: int) -> list[tuple[str, int]]:
    raise NotImplementedError


def monthly_pivot_pd(rows: list[dict]) -> dict[str, dict[str, int]]:
    raise NotImplementedError


if __name__ == "__main__":
    from problem_api import load_rows

    rows = load_rows()
    print(total_by_annotator(rows))
    print(top_n_annotators(rows, 3))
    for project, months in monthly_pivot(rows).items():
        print(f"{project:<8}", months)
