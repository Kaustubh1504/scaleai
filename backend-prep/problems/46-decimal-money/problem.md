# 46. Money with Decimal

The payouts team found annotators being paid a cent short. The cause: dollar
amounts parsed with `float` and summed. You're writing the small money helpers
everyone else will call. Store money as **integer cents**; use `Decimal` at the
edges (parsing, percentages, rounding).

## Input

Dollar amounts arrive as strings from CSVs and APIs: `"12.34"`, `"$1,234.50"`,
`" 7 "`, `".5"`. Tax rates arrive as strings of percent, e.g. `"8.875"`.

## Setup

There is no `problem_api`: tests call your functions directly with strings and
ints, and import `ROUND_HALF_UP` / `ROUND_HALF_EVEN` from `decimal` to pass as
`rounding`. Your file starts empty. An `if __name__ == "__main__":` block is what
the Run button executes: use it to see why floats and money don't mix
(`0.1 + 0.2`, `round(1.005, 2)`, `Decimal(0.1)`, `Decimal("1e3")`).

## Your task

Write in your file:

* `parse_dollars(s: str) -> int`
* `split_cents(total_cents: int, n: int) -> list[int]`
* `tax_cents(amount_cents: int, rate_percent: str | Decimal, rounding: str = ROUND_HALF_UP) -> int`
* `total_dollars(amounts: Iterable[str]) -> Decimal`

Rules:

* `parse_dollars`: returns exact integer cents. Surrounding whitespace, one
  leading `$` and `,` thousands separators are allowed. At most **2** decimal
  places. Negative amounts, empty strings, more decimals (`"1.234"`), exponents
  (`"1e3"`), `"NaN"`/`"inf"` and other junk raise `ValueError`.
* `split_cents`: split `total_cents` into `n` parts that sum to the total and
  differ by at most 1 cent; the leftover cents go to the **first** parts.
  `n < 1` raises `ValueError`.
* `tax_cents`: `amount_cents * rate_percent / 100`, rounded to a whole cent
  with the given `decimal` rounding mode (`ROUND_HALF_UP` by default; callers
  may pass `ROUND_HALF_EVEN`, banker's rounding). `rate_percent` must be a
  `str` or `Decimal`; a `float` raises `TypeError` (floats can't represent
  rates like 8.875% exactly in general, so we refuse them).
* `total_dollars`: exact sum of decimal strings, returned as a `Decimal`
  quantized to cents (`Decimal("0.01")`) with `ROUND_HALF_UP`. Inputs here are
  plain decimal strings (may have more than 2 places). An empty input gives `Decimal("0.00")`.

## Example

```python
parse_dollars("$1,234.5")                     # 123450
split_cents(1000, 3)                          # [334, 333, 333]
tax_cents(50, "5")                            # 3   (2.5 -> 3)
tax_cents(50, "5", rounding=ROUND_HALF_EVEN)  # 2   (2.5 -> 2, to even)
total_dollars(["0.10", "0.20"])               # Decimal("0.30")  (0.1 + 0.2 == 0.30000000000000004 as floats)
total_dollars(["1.005"])                      # Decimal("1.01")  (float 1.005 is 1.00499999...)
```

## Constraints

* Never pass a value through `float`. Build `Decimal`s from strings (or ints).

<details><summary>Hint 1</summary>

Validate the cleaned string with `re.fullmatch` (digits, optional dot, at most
two decimals; `.5` allowed) before `Decimal(...)`: `Decimal` happily accepts `"1e3"`,
`"NaN"` and `"-0"`.
</details>

<details><summary>Hint 2</summary>

Multiply and divide as `Decimal`s, then `quantize(Decimal("1"), rounding=rounding)`
to get whole cents. `divmod(total, n)` gives the base share and the leftover.
</details>

## Follow-up (talk it through)

* Why store integer cents in the database rather than `NUMERIC(12, 2)` or a float?
  What about currencies with 0 or 3 decimal places (JPY, KWD)?
* A payout is split across 3 projects and each line is rounded separately.
  Why might the lines not sum to the total, and how do you fix it?
