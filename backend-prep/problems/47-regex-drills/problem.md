# 47. Regex drills

Support tickets and request logs from an annotation platform need light text
processing: pull out references, validate client-supplied keys, parse log
lines and scrub PII before the text goes to an LLM labeling queue.

## Input

```
2024-05-01T12:00:03Z GET /v1/tasks/t_19 200 35ms req=ab12-x
```

Log line format: ISO timestamp ending in `Z`, method (`GET|POST|PUT|PATCH|DELETE`),
path (starts with `/`, no spaces), 3-digit status, latency as an integer
followed by `ms`, then `req=<request id>` (`[A-Za-z0-9-]+`). Fields are
separated by single spaces.

## Setup

There is no `problem_api`: tests call your functions directly with strings
(and, for the key validator, also `None` and ints). Your file starts empty. An
`if __name__ == "__main__":` block is what the Run button executes: use it to try
the classic traps (`findall` with a group, `$` before a trailing newline).

## Your task

Write in your file:

* `find_tickets(text: str) -> list[str]`
* `find_emails(text: str) -> list[str]`
* `is_valid_idempotency_key(key: object) -> bool`
* `parse_log_line(line: str) -> dict | None`
* `redact_pii(text: str) -> str`

Rules:

* `find_tickets`: refs are `TKT-` + 1 to 6 digits, as a whole word
  (`XTKT-1` and `TKT-1234567` are not refs). Case-sensitive. Return each ref
  once, in order of first appearance.
* `find_emails`: `local@domain` where local is `[A-Za-z0-9._%+-]+` and domain
  is labels of `[A-Za-z0-9-]+` joined by dots, with at least one dot. Return
  them **lower-cased**, de-duplicated, in order of first appearance. A
  sentence-ending `.` is not part of the email.
* `is_valid_idempotency_key`: `True` only for a `str` of 1–64 characters from
  `[A-Za-z0-9_-]`, with nothing else (not even a trailing newline); any non-`str` is `False`.
* `parse_log_line`: returns `{"ts", "method", "path", "status", "latency_ms",
  "request_id"}` with `status` and `latency_ms` as `int`s, or `None` if the
  line doesn't match the format exactly (a trailing `\n` is fine).
* `redact_pii`: replace each email with `[EMAIL]` and each phone number with
  `[PHONE]`. A phone number is an optional `+1` followed by a space or `-`,
  then 3 digits (optionally in parentheses), a separator, 3 digits, a
  separator and 4 digits, where each separator is one space, `-` or `.`, and
  the whole thing is not touching other digits. 10 bare digits are **not** a phone.

## Example

```python
find_tickets("See TKT-12 and TKT-9, dup TKT-12")           # ["TKT-12", "TKT-9"]
find_emails("Mail Bob@Example.com or ann@x.co.uk.")         # ["bob@example.com", "ann@x.co.uk"]
is_valid_idempotency_key("order-42_retry")                  # True
redact_pii("call (415) 555-0123 or +1 415.555.0199, ann@x.io")
# "call [PHONE] or [PHONE], [EMAIL]"
```

## Constraints

* Compile patterns once at module level. Use the `re` module only.

<details><summary>Hint 1</summary>

`re.findall` returns the **groups** when the pattern has any. Use `(?:...)`
for grouping you don't want back, or `finditer` + `m.group(0)`.
</details>

<details><summary>Hint 2</summary>

`re.match(r"[A-Za-z0-9_-]{1,64}$", "abc\n")` matches, because `$` also matches
before a trailing newline. `re.fullmatch` doesn't have that hole. Use
`(?<!\d)` / `(?!\d)` to stop a phone pattern matching inside a longer number.
</details>

## Follow-up (talk it through)

* What PII would this redactor miss? Would you trust regex alone before sending text to a third-party model?
* When does a regex become the wrong tool for parsing a log format?
