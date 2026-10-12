# 42. Write the tests: catch the buggy clients

A teammate wrote `fetch_all()`, the client that pulls every label out of the
Labels API with retries. It's correct today. Your job is to make sure it
**stays** correct: write the test suite. The judge runs your tests against the
real client (they must all pass) and against **8 subtly broken versions**
(mutants). A mutant is *caught* when at least one of your tests fails on it.
Each judge case is named after the bug its mutant contains.

## The API

`GET /v1/labels?page=<N>` (pages start at 1):

```json
{"data": [{"id": "lbl_001", "task_id": "task_001", "label": "dog"}, ...],
 "page": 1, "total_pages": 3, "next_page": 2}
```

`next_page` is `null` on the last page. `problem_api.make_api(n_labels=25, per_page=10)`
builds a mock of it (`kit.MockAPI`): `api.labels` holds every label,
`api.script("GET /v1/labels", [503, "429:7", 404, "pass"])` injects responses
in order, `api.log` records every request.

## The client's contract

The module under test (`impl`) exposes exactly:

* `impl.ApiError(Exception)`: has `.status: int`.
* `impl.fetch_all(client: httpx.Client, clock, *, max_attempts: int = 4, base_delay_s: float = 0.5) -> list[dict]`

Behaviour:

* Returns every label from every page, in API order, following `next_page`.
* Each page request is tried at most `max_attempts` times. Only **503** and
  **429** are retried. Before retry number *k* (k = 1, 2, ...) it calls
  `clock.sleep(d)` where `d` is the `Retry-After` value (seconds) for a 429
  that has the header, otherwise `base_delay_s * 2 ** (k - 1)`.
* It never sleeps after the last attempt: it raises `ApiError(status)`.
* Any other non-2xx status raises `ApiError(status)` immediately, with no retry.
* An error on any page raises; it never returns partial results.

## Setup

```python
import pytest
from kit import FakeClock            # clock.sleep(s) records into clock.sleeps; never really sleeps
from problem_api import make_api     # api = make_api(n_labels=25, per_page=10); api.client() -> httpx.Client
```

`api.log` is a list of `Call`s (`.params`, `.status`); `api.script(...)` is shown
above; `"429:7"` means 429 with `Retry-After: 7`. Your file starts empty. An
`if __name__ == "__main__":` block is what the Run button executes: there you
may `import client_impl` (the correct client) and call your tests on it directly,
e.g. `test_x(client_impl)`.

## Your task

Write test functions in your file:

* Each is a module-level function named `test_*` taking exactly one parameter,
  `impl` (the client module: use `impl.fetch_all` and `impl.ApiError`).
* Build everything else (mock API, `FakeClock`) inside the test. Use plain
  `assert`s and `pytest.raises`. Anything a test raises counts as a failure.
* The judge collects every `test_*` function defined in your file and calls
  `test_x(impl)` itself (no fixtures). All of them must pass against the correct
  client; only those that do count towards catching mutants.

## Example

```python
def test_single_page(impl):
    assert impl.fetch_all(make_api(n_labels=5).client(), FakeClock())[0]["id"] == "lbl_001"
```

This passes against the correct client, but every mutant passes it too, so it
catches nothing. Write tests until all 8 are caught.

## Constraints

* No real sleeps, no network: use `FakeClock` (`clock.sleeps` lists every
  wait) and the mock API (`len(api.log)` counts attempts).
* Test behaviour from the contract above, not the implementation's internals.

<details><summary>Hint 1</summary>

For each rule in the contract, ask: "what's the cheapest wrong implementation,
and which assertion would notice?" Exact `==` on the whole result, the number
of requests and the exact `clock.sleeps` list catch far more than `len(...) > 0`.
</details>

<details><summary>Hint 2</summary>

Cover the boundaries: a multi-page happy path, `[503, 503]` then success,
`["429:7"]`, a 404, exactly `max_attempts` failures, `max_attempts - 1`
failures then success, and a failure on page 2 after page 1 succeeded.
</details>

## Follow-up (talk it through)

* What's the difference between line coverage and mutation score? Which would you put in CI?
* Which of these tests would you rather write against a real staging API, and why not all of them?
