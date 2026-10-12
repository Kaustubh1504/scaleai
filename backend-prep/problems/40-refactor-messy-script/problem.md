# 40. Refactor a messy payout script

Finance runs `payouts.py` every Friday. It works, but it's one 100-line
function: diagnostics are `print`ed into the report, errors `sys.exit(1)` from
deep inside, the API key and URL are hard-coded, a bare `except:` hides bugs,
pagination is copy-pasted, and the pay rates are magic numbers. Nobody can test
it. Your starter file **is** that script. Refactor it into small, typed,
testable pieces **without changing the report it prints**.

## The API

`GET /v1/annotators` and `GET /v1/submissions`, both
`?page=<1..>&per_page=<1..100>`, header `Authorization: Bearer <key>`:

```json
{"data": [{"id": "ann_001", "name": "Ada Okafor", "level": "senior", "active": true}],
 "page": 1, "per_page": 50, "total": 7, "total_pages": 1}
```

Submissions look like `{"id": "sub_001", "annotator_id": "ann_002", "task_type": "bbox", "status": "accepted"}`.

## Setup

```python
from problem_api import ENV, make_api     # ENV: the two required PAYOUT_* variables
api = make_api(); http = api.client()     # mock API; api.script("GET /v1/annotators", [503]) injects failures
main([], dict(ENV), http)                 # how the tests drive your refactored script
```

Your starter file holds the old script. Its `if __name__ == "__main__":` block is
what the Run button executes: run it first to see the report you must preserve.

## Your task

Replace `do_everything` with these names (tests use all of them):

* `ConfigError(Exception)`
* `ApiError(Exception)`: constructed as `ApiError(status, path)`, with attributes `.status: int` and `.path: str`.
* `Config`: frozen dataclass, fields in order `base_url: str, api_key: str, timeout_s: float = 10.0, per_page: int = 50`.
* `Payout`: frozen dataclass, fields in order `annotator_id: str, name: str, tasks: int, amount_cents: int` (tests compare against `Payout("a2", "A2", 3, 47)`).
* `load_config(env: Mapping[str, str]) -> Config`
* `ApiClient(http: httpx.Client, config: Config)` with `.paginate(path: str) -> Iterator[dict]`
* `compute_payouts(annotators: list[dict], submissions: list[dict]) -> list[Payout]`
* `format_summary(payouts: list[Payout]) -> str`
* `main(argv: list[str], env: Mapping[str, str], http: httpx.Client | None = None) -> int`

Rules:

* **`load_config`**: `PAYOUT_API_URL` and `PAYOUT_API_KEY` are required
  (missing or blank is an error); `PAYOUT_TIMEOUT_S` (float `> 0`, default 10)
  and `PAYOUT_PER_PAGE` (int `1..100`, default 50) are optional. Any problem
  raises `ConfigError` whose message names the variable.
* **`ApiClient.paginate`**: a generator yielding every item of `data`, page 1
  upwards, until `page >= total_pages`. Every request goes through `http`
  (its `base_url` is set) with `page`, `per_page=config.per_page` and the
  bearer header. A non-2xx response **or** a body that isn't valid JSON raises
  `ApiError(status, path)`. Log one `DEBUG` message per page.
* **`compute_payouts`** (the script's rules, unchanged): only `active`
  annotators; only `"accepted"` submissions; submissions from unknown or
  inactive annotators are ignored. Rates in cents: `bbox` 12, `classify` 5,
  `transcribe` 30. Any other `task_type` is skipped with a `WARNING` log that
  includes the submission id. `senior` annotators get +25%, rounded **half up**
  to a whole cent. Only annotators with at least one paid task appear. Sort by
  `amount_cents` descending, then `annotator_id` ascending.
* **`format_summary`**: exactly the lines the old script printed, joined with
  `"\n"` (no trailing newline).
* **`main`**: returns an exit code. `0`: printed the summary to stdout (or,
  with `"--json"` in `argv`, a JSON array of objects with keys
  `annotator_id, name, tasks, amount_cents`). `2`: bad config (no requests
  made). `1`: `ApiError`. For 1 and 2, log an `ERROR` and print nothing. If
  `http` is `None`, `main` creates (and closes) its own `httpx.Client` from the config.
* Diagnostics go through `logger = logging.getLogger(__name__)`. **No
  `print` outside `main`**, no `sys.exit` (except `sys.exit(main(...))` in
  the `__main__` block), no bare `except:`, and no hard-coded key or URL
  anywhere in the file.

## Example

```
PAYOUT SUMMARY
ann_001  Ada Okafor              6 tasks  $0.90
ann_007  Gus Albright            1 tasks  $0.38
TOTAL $1.28 across 2 annotators
```
(Run the starter to see the full report for the sample data.)

## Constraints

* The printed report must stay byte-for-byte identical: finance diffs it.
* Keep money in integer cents.
* For your `__main__` block, use `problem_api.ENV` and `make_api().client()`
  (that's how the key stays out of your file), e.g. `sys.exit(main(sys.argv[1:], ENV, make_api().client()))`.

<details><summary>Hint 1</summary>

Do it in safe steps: pull out `paginate` first (kills the duplication), then
`compute_payouts` (pure: no I/O, easy to test), then `format_summary`, and
finally make `main` the only place that knows about exit codes and stdout.
</details>

<details><summary>Hint 2</summary>

`main` is the only place that catches: `ConfigError` → log an error and return 2,
`ApiError` → log and return 1. Inside `paginate`, `except ValueError` around
`resp.json()` replaces the bare `except:` (`json.JSONDecodeError` is a `ValueError`).
</details>

## Follow-up (talk it through)

* What would you test first if you could only write three tests for this script?
* Finance now wants a CSV export too. Where does it plug in, and what didn't you have to touch?
* How would you make the rates configurable without a redeploy, and what are the risks?
