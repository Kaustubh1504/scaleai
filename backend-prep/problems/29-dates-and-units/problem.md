# 29. Timestamps, durations and money units

Annotator time-tracking data comes from three vendors and a spreadsheet.
Timestamps arrive as ISO strings, US dates or epoch numbers (sometimes in
milliseconds); durations as `"90s"` or `"01:30:00"`; payouts as `"$12.30"` or
`"1230c"`; shift starts as local wall-clock times. Payroll runs on these
numbers, so each parser returns one canonical form or raises `ValueError`.

## Input

Single values (`str`, `int`, `float`, `datetime`, ...). See
`problem_api.SAMPLE_ROWS` for a realistic mix.

## Setup

```python
from problem_api import SAMPLE_ROWS   # list of row dicts, values exactly as received
```

The `if __name__ == "__main__":` block is what the Run button executes: print
the sample rows there to see every format (and Python type) you must handle.

## Your task

Your module must define:

* `parse_timestamp(v) -> datetime`: always timezone-aware, in UTC
* `to_iso_z(dt: datetime) -> str`
* `parse_duration(v) -> float`: seconds
* `parse_money_cents(v) -> int`
* `local_to_utc(naive_str: str, tz_name: str) -> datetime`: aware, in UTC

**`parse_timestamp`** (strings are stripped first):

| input | meaning |
|---|---|
| `datetime` | naive = UTC; aware is converted to UTC |
| `int`/`float`, or a string matching `-?\d+(\.\d+)?` | epoch: **seconds**, or **milliseconds** if `abs(n) >= 10**11` |
| ISO 8601: `"2024-03-01T10:00:00Z"`, `"...+05:30"`, `"2024-03-01 10:00"`, `"2024-03-01"` | `Z` and offsets honoured; no offset = UTC |
| a string containing `/` | US only: `MM/DD/YYYY`, `MM/DD/YYYY HH:MM`, `MM/DD/YYYY HH:MM:SS` (UTC) |
| `bool`, `""`, `"yesterday"`, `"13/01/2024"`, NaN, anything else | `ValueError` |

Keep sub-second precision exactly to the microsecond (`"1709290800123"` →
`.123000`, `"1709290800.5"` → `.500000`).

**`to_iso_z(dt)`**: convert to UTC and format as `YYYY-MM-DDTHH:MM:SSZ`, with
`.ffffff` (6 digits) before the `Z` only when microseconds are non-zero. A
**naive** `dt` raises `ValueError` (don't guess its zone).

**`parse_duration`** returns float seconds; negative or non-finite raises:

* `int`/`float`: seconds. A bare numeric string `"45"`, `"2.5"`: seconds.
* Clock: `"MM:SS"` (`"1:30"` → 90) or `"HH:MM:SS"` (`"01:30:00"` → 5400;
  seconds may be fractional). Minutes/seconds after the first field must be `00`–`59`.
* One or more `<number><unit>` parts, case-insensitive, spaces allowed:
  units `ms`, `s`/`sec`, `m`/`min`, `h`/`hr`. `"1500ms"` → 1.5,
  `"1.5m"` → 90, `"1h30m"` → 5400, `"2m 30s"` → 150.
* Anything else (`"-5s"`, `"5x"`, `"1:75"`, `"h"`, `""`, `True`) → `ValueError`.

**`parse_money_cents`** returns integer cents, using `Decimal` (never float math):

* Bare numbers are **dollars**: `12` → 1200, `"12"` → 1200, `"12.3"` → 1230,
  `19.99` (float) → 1999, `Decimal("0.5")` → 50.
* Strings: optional `-`, optional `$`, then digits with optional thousands
  commas (`"$1,000.00"` → 100000); an optional `USD` prefix or suffix
  (case-insensitive, `"USD 12.30"`, `"12.30 usd"`).
* Cents: an integer followed by `c`, `cents` or `¢` (`"1230c"`, `"1230 cents"`,
  `"-120c"`). `"12.5c"` → `ValueError`.
* If the amount is not a whole number of cents (`"$12.345"`, `0.1 + 0.2`),
  raise `ValueError`: never round silently. `bool` and junk also raise.

**`local_to_utc(naive_str, tz_name)`**: `naive_str` is an ISO local wall time
(`"2024-07-01 09:00"`) in IANA zone `tz_name`. Return the UTC instant.

* An unknown zone, an unparseable string, or a string that **has** an offset → `ValueError`.
* A time that doesn't exist (spring-forward gap, e.g. `"2024-03-10 02:30"` in
  `America/New_York`) → `ValueError`.
* A time that happens twice (fall-back, `"2024-11-03 01:30"` in New York) → the
  **earlier** instant (`05:30Z`, still on daylight time).

## Example

```python
to_iso_z(parse_timestamp("03/01/2024 14:15"))       # "2024-03-01T14:15:00Z"
to_iso_z(parse_timestamp(1709290800123))            # "2024-03-01T11:00:00.123000Z"
parse_duration("2m 30s")                            # 150.0
parse_money_cents("$1,234.56"), parse_money_cents("1230c")   # 123456, 1230
local_to_utc("2024-07-01 09:00", "Asia/Kolkata")    # 2024-07-01 03:30:00+00:00
```

## Constraints

* Standard library only (`datetime`, `zoneinfo`, `decimal`, `re`).
* Raise `ValueError` for bad input, never `KeyError`/`InvalidOperation`/`OverflowError`.

<details><summary>Hint 1</summary>

`datetime.fromisoformat` handles offsets, a space separator and date-only
strings; replace a trailing `Z` with `+00:00` first for Python 3.10.
`ZoneInfoNotFoundError` is a subclass of `KeyError`, not `ValueError`.
</details>

<details><summary>Hint 2</summary>

`zoneinfo` never raises for a non-existent local time: it quietly picks an
offset. Detect the gap with a round trip: convert to UTC and back, and check
you get the same wall-clock time. `fold=0` (the default) is the earlier of two
repeated times.
</details>

<details><summary>Hint 3</summary>

`int(19.99 * 100)` is `1998`. Go through `Decimal(str(v))`, multiply by 100,
and check the result is integral before converting.
</details>

## Follow-up (talk it through)

* Why is "naive means UTC" acceptable for input but not for output?
* An epoch value of `1709290800` arrives as a float `1709290800.0000002`.
  What precision guarantees can you actually give, and where would you store
  timestamps to avoid this?
* A shift in London is scheduled for 01:30 on the fall-back night. Is "earlier"
  the right policy for payroll? Who should decide?
