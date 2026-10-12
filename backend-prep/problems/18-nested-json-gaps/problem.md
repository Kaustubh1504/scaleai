# 18. Nested JSON with gaps

The annotator directory has been through three API versions, and the export
you've been handed mixes all of them. v1 is flat (`name`, `email`, `city`),
v2 nests everything (`profile.full_name`, `contact.email`, `address.city`),
v3 has a list of addresses and splits names in two. Values are missing,
`null`, the *string* `"null"`, or just `""`. You need one flat, clean profile
per record without a single `KeyError` or `TypeError`.

## Input

A list of dicts (see `problem_api.RECORDS`), for example:

```json
{"annotator_id": 2,
 "profile": {"full_name": "Diego Alvarez", "skills": ["audio", " ocr "]},
 "contact": {"email": "diego@example.com"},
 "address": {"country": "MX", "city": "Monterrey"},
 "stats": {"rating": 4.1}, "status": "Active"}
```

## Setup

```python
from problem_api import RECORDS     # 4 records: v1, v2, v3 and a nearly empty one
```

No HTTP: these are pure functions. The `if __name__ == "__main__":` block is
what the Run button executes: pretty-print each record there
(`json.dumps(rec, indent=2)`) to see the shapes before you write the mapping.

## Your task

Your module must define:

* `get_path(obj, path: str, default=None)`: returns the value found, or `default`
* `to_profile(record: dict) -> dict`

**`get_path`** follows a dotted path such as `"addresses.0.city"`:

* Split `path` on `"."`. An empty path `""` returns `obj` itself.
* On a **dict**, the segment is a key (`"0"` is the string key `"0"`).
* On a **list**, the segment must be a non-negative integer in range
  (`"0"`, `"12"`); `"-1"`, `"x"` or an out-of-range index gives `default`.
* On anything else (`None`, a string, a number) the walk stops: `default`.
* It **never raises**. A key that *exists* with value `None` returns `None`
  (not `default`): `get_path({"a": None}, "a", "x") -> None`.

**`to_profile`** returns a dict with exactly these keys. For each field, try
the sources in order and use the first one that is **not blank**:

| field     | sources, in order | conversion | if all blank |
|-----------|-------------------|------------|--------------|
| `id`      | `id`, `annotator_id` | str or int (not bool) → `str(v).strip()` | raise `ValueError` |
| `name`    | `name`, `profile.full_name`, then `profile.first_name` + `" "` + `profile.last_name` (the non-blank parts, joined) | strip | `None` |
| `email`   | `email`, `contact.email` | strip, lower-case | `None` |
| `country` | `country`, `address.country`, `addresses.0.country` | strip, upper-case | `None` |
| `city`    | `city`, `address.city`, `addresses.0.city` | strip | `None` |
| `skills`  | `skills`, `profile.skills` | list → its string items; string → split on `","`; each stripped, blank items dropped, order kept | `[]` |
| `rating`  | `rating`, `stats.rating` | int / float (not bool) or numeric string → `float` | `None` |
| `active`  | `active`, then `status` | `active`: a bool, or the string `"true"`/`"false"` (any case); `status`: `True` iff it equals `"active"` (any case) | `False` |

A source is **blank** if it is missing, `None`, a string that is empty /
whitespace / `"null"` (any case) after stripping, the wrong type for the field
(`name`, `email`, `country`, `city` take strings only), a value the
conversion rejects (`rating: "n/a"`, `active: "yes"`), or a `skills` value
that leaves no items. Blank sources are skipped.

## Example

```python
get_path({"addresses": [{"city": "Pune"}]}, "addresses.0.city")   # "Pune"
get_path({"addresses": []}, "addresses.0.city", "?")              # "?"

to_profile(RECORDS[2])
# {"id": "ann_003", "name": "Mei Lin", "email": "mei@example.com", "country": "SG",
#  "city": None, "skills": [], "rating": 3.0, "active": False}
```

## Constraints

* Don't mutate the input record.
* `to_profile` must not raise for any record that has an id, however broken
  the rest of it is.

<details><summary>Hint 1</summary>

Write a `first(record, *paths, convert)` helper: for each path, `get_path`,
try `convert`, return the first non-`None` result. Each conversion returns
`None` for "blank", so the table becomes one line per field.
</details>

<details><summary>Hint 2</summary>

`isinstance(True, int)` is `True` in Python. Check for `bool` before `int`.
</details>

## Follow-up (talk it through)

* `get_path` returns `None` for a present-but-null key and `default` for a
  missing one. When does that distinction matter downstream?
* A fourth API version ships next month. How would you structure the field
  mapping so adding it is a data change, not a code change?
* Would you log or count which source each field came from? What would you do
  with those numbers?
