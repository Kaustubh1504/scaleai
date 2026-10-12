# 20. Validating messy records with Pydantic

Annotator sign-ups arrive from three intake forms (a web form, a CSV upload
and a partner API). Ops wants one rule: **every record is either loaded as a
clean `Annotator` or reported back with the field that broke it**, so the
partner can fix the source. Nothing crashes the batch, nothing is silently
coerced into nonsense (`True` is not an age).

## Input

A list (see `problem_api.RAW_RECORDS`). Items are usually dicts but not always:

```python
{"id": " ann_101 ", "email": "Priya.Raman@Example.COM", "age": "29",
 "tags": "NER, sentiment, ner", "joined_at": "2024-03-01T10:00:00Z", "referrer": "campus"}
"ann_107,fatima@example.com,30"          # a raw CSV line slipped through
```

## Setup

```python
from problem_api import RAW_RECORDS     # 9 items from the three forms
```

No HTTP. The `if __name__ == "__main__":` block is what the Run button
executes: print each raw record there, and try `Annotator.model_validate(...)`
on a record with `"age": True` to see what Pydantic does by default.

## Your task

Your module must define:

* `class Annotator(pydantic.BaseModel)`, fields declared in this order:
  `id: str`, `email: str`, `age: int | None = None`,
  `tags: list[str] = []` (use a default factory), `joined_at: datetime`.
* `parse_records(raw: list) -> tuple[list[Annotator], list[dict]]`

Field rules (fields are validated **in this order**: `id`, `email`, `age`, `tags`, `joined_at`):

| field | accepts | result | rejects |
|-------|---------|--------|---------|
| `id` | a string | stripped | non-strings; blank after stripping |
| `email` | a string | stripped, lower-cased; must match `^[^@\s]+@[^@\s]+\.[^@\s]+$` | anything that doesn't match |
| `age` | an int, or a string of digits (surrounding spaces ok); missing / `None` / `""` → `None` | int in **16..99** | bools, floats, `"42.5"`, `"abc"`, out of range |
| `tags` | `"a, b"` (split on `,`) or a list of strings; missing / `None` → `[]` | each stripped and lower-cased, blanks dropped, **deduplicated keeping first occurrence** | a list containing non-strings, other types |
| `joined_at` | an ISO 8601 **string** with `Z`, an offset, or no offset (naive means UTC) | timezone-aware datetime **in UTC** | non-strings (no unix timestamps), unparseable strings |

* `id`, `email`, `joined_at` are required. Unknown keys are ignored.

**`parse_records(raw)`** returns `(valid, errors)`:

* `valid`: `Annotator` instances for the items that validated, in input order.
* `errors`: one dict per invalid item, in input order:
  `{"index": <position in raw>, "field": <name>, "message": <str>}`.
  Report only the **first** failing field in the order above. If the item
  isn't a dict at all, `field` is `None`.

## Example

```python
valid, errors = parse_records(RAW_RECORDS)
valid[1].joined_at        # datetime(2024, 3, 1, 10, 30, tzinfo=timezone.utc)  (was 12:30+02:00)
valid[0].tags             # ["ner", "sentiment"]
errors[0]                 # {"index": 2, "field": "email", "message": "Value error, not a valid email address"}
```

The exact `message` text is up to you; it must be a non-empty string.

## Constraints

* Use Pydantic v2 (`field_validator`, `model_validate`). Code should run on Python 3.10+.
* Never let a bad item raise out of `parse_records`.

<details><summary>Hint 1</summary>

`@field_validator("age", mode="before")` runs on the raw input before
Pydantic's own coercion, which is where you reject `True` (Pydantic happily
turns it into `1`). A plain (after) validator gets the already-parsed value,
which is where you strip, lower-case, or convert to UTC.
</details>

<details><summary>Hint 2</summary>

`except ValidationError as exc: exc.errors()` is a list of dicts with
`"loc"` (a tuple such as `("age",)`, or `()` when the whole input was the wrong
type) and `"msg"`. Errors come back in field-definition order.
</details>

## Follow-up (talk it through)

* You report only the first error per record. When would a partner prefer
  all of them, and what would change?
* Is "naive means UTC" a safe default? What would you ask the form owners?
* 2 % of a 1M-row batch fails validation. Load the rest or reject the batch?
