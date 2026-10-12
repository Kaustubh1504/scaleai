# 28. Normalize messy field values

A customer uploads task metadata as a spreadsheet export before every labeling
batch. The same column arrives as `"$1,234.50"`, `"(5.00)"` or `"12%"`;
booleans are `"Yes"`, `" ON "` or `0`; ids lose their leading zeros. You are
writing the small, strict **value normalizers** that the ingestion pipeline
calls on every cell. Strict means: either a precise answer or a `ValueError`,
never a silent guess.

## Input

Single cell values: `str`, `int`, `float`, `bool`, `Decimal` or `None`, as
produced by `csv`/`json`/spreadsheet readers. `problem_api.SAMPLE_ROWS` has a
few real-looking rows and `LABEL_MAPPING` a category config.

## Setup

```python
from problem_api import LABEL_MAPPING, SAMPLE_ROWS   # a dict config and a list of row dicts
```

The `if __name__ == "__main__":` block is what the Run button executes: print
each sample row and the Python type of every value there before writing rules.

## Your task

Your module must define:

* `parse_missing(v) -> Any`: `None`, or `v` (strings stripped)
* `parse_number(v) -> Decimal | None`
* `parse_bool(v) -> bool | None`
* `split_multi(v) -> list[str]`
* `normalize_id(v) -> str | None`
* `normalize_category(v, mapping: dict[str, list[str]]) -> str | None`

**Missing values.** `parse_missing(v)` returns `None` when `v` is `None`, a
float NaN, or a string whose stripped, lower-cased form is one of
`"" "n/a" "na" "null" "none" "nan" "-"`. Any other string is returned
**stripped**; any other value is returned unchanged (`0`, `0.0` and `False` are
real values). Every other function first applies this rule: a missing input
returns `None` (`split_multi` returns `[]`).

**`parse_number`** returns a `Decimal`, never a float:

| input | result |
|---|---|
| `"42"`, `" 3.50 "`, `".5"` | `Decimal("42")`, `Decimal("3.50")`, `Decimal("0.5")` |
| `"1,234.50"`, `"$1,234,567"` | commas only as thousands groups of 3: `Decimal("1234.50")`, `Decimal("1234567")` |
| `"-$5"`, `"+7"` | optional leading sign, then optional `$`: `Decimal("-5")`, `Decimal("7")` |
| `"(5.00)"`, `"($1,000)"` | accounting negative: `Decimal("-5.00")`, `Decimal("-1000")` |
| `"12%"`, `"-2.5%"` | divided by 100 exactly: `Decimal("0.12")`, `Decimal("-0.025")` |
| `"1e3"`, `"2.5E-2"` | scientific (no commas): equal to `1000`, `0.025` |
| `7`, `0.1`, `Decimal("2.5")` | `Decimal(7)`, `Decimal("0.1")` (via `str`, not the binary float), unchanged |
| `True`, `float("inf")`, `"inf"`, `"12,34"`, `"1.2.3"`, `"$"`, `"--5"`, `"(-5)"`, `"$5%"`, `"12abc"` | `ValueError` |

Grammar (after stripping): either `(`*body*`)` or an optional `+`/`-` before
the body; the body is an optional `$`, a number, and an optional `%` (never
both `$` and `%`).

**`parse_bool`**: `bool` is returned as is; `int` `1`/`0` → `True`/`False`.
Strings, stripped and case-insensitive: `true t yes y 1 on` → `True`,
`false f no n 0 off` → `False`. Everything else (`"maybe"`, `2`, `1.0`) raises
`ValueError`. (`bool("false")` is `True`: don't.)

**`split_multi`** splits a string on any of `;` `|` `,`, strips each part, drops
empty parts and removes duplicates keeping the **first** occurrence's order
(case-sensitive). A list/tuple of strings is treated as already-split chunks,
each of which is split the same way. `"a; b|c, ,a"` → `["a", "b", "c"]`.

**`normalize_id`**: strings are stripped and upper-cased and must then match
`[A-Z0-9_-]+` (leading zeros kept: `" 007 "` → `"007"`, `"ann-07"` → `"ANN-07"`).
A non-negative `int` becomes `str(v)`. Raise `ValueError` for **any float**
(`7.0` means a spreadsheet already ate the leading zeros), `bool`, negative
ints, and strings with other characters (`"T 9"`, `"7.0"`).

**`normalize_category`**: `mapping` is `{canonical: [synonyms...]}`. Matching
ignores case, treats `_` and `-` as spaces and collapses runs of whitespace;
the canonical name itself also matches. Return the canonical key exactly as
written in `mapping`. Unknown values or non-strings raise `ValueError`. If two
different canonicals share a name after this normalization, the mapping is
broken: raise `ValueError` (even for an input that would otherwise match).

## Example

```python
parse_number("($1,234.50)")                      # Decimal("-1234.50")
parse_bool(" ON ")                               # True
split_multi(["night; rain", "rain|fog"])         # ["night", "rain", "fog"]
normalize_id(7.0)                                # ValueError
normalize_category("motor_vehicle", LABEL_MAPPING)  # "vehicle"
normalize_category("  N/A ", LABEL_MAPPING)      # None
```

## Constraints

* Standard library only. Never round-trip money through `float`.
* Raise `ValueError` (not `TypeError`, `InvalidOperation` or `KeyError`) for bad input.

<details><summary>Hint 1</summary>

Write `parse_missing` first and call it at the top of every other function.
Check `isinstance(v, bool)` **before** `isinstance(v, int)`: `True` is an `int`.
</details>

<details><summary>Hint 2</summary>

`Decimal("inf")` and `Decimal("1,234")` behave differently from what you want,
so validate the text with a `re.fullmatch` first. `Decimal.scaleb(-2)` divides
by 100 without any rounding.
</details>

## Follow-up (talk it through)

* `"12,34"` is twelve point three four in a German export. How would you
  support locales without making the US case ambiguous?
* These functions raise on bad input. Where in a pipeline do you catch that,
  and what do you record so a human can fix the source row?
