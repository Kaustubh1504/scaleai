# Authoring guide

How to add a problem. Read `problems/09-cursor-pagination/` first: it is the
reference example, and every problem follows its shape.

## Goal

Practice for the **Scale AI backend round**: a 60-minute, open-book coding
round where the candidate queries a mock API or processes messy data, writes
correct, robust, readable Python, and talks through the decisions. Problems
should feel like realistic slices of that work (annotation platforms,
tasks, annotators, customers, payouts, documents, LLM labels, ...), **not**
puzzles. Correctness rules must be unambiguous so the tests are fair.

## Layout

```
problems/<id>-<slug>/
  meta.json         {"id", "title", "group", "level", "minutes", "daily", "tags", "parts"}
  problem.md        the statement (rendered in the UI)
  starter.py        what the candidate starts with: signatures + NotImplementedError stubs
  solution.py       reference solution (clean, idiomatic, the code you'd want to see)
  test_problem.py   the tests the judge runs
  problem_api.py    optional: make_api(...) / sample data shared by tests and __main__
  data/             optional: sample files (CSV, JSONL, ...)
```

* `id` is a two-digit string (`"07"`) or `"M1"`..`"M4"` for mock rounds. The
  dir name is `<id>-<kebab-slug>`.
* `group` is exactly one of:
  `"1. HTTP and API basics"`, `"2. Exploring an unknown API"`, `"3. Querying robustly"`,
  `"4. Parsing and processing"`, `"5. Data cleaning"`, `"6. Concurrency"`,
  `"7. Building a service"`, `"8. Production quality"`, `"9. Python fluency"`,
  `"Mock rounds"`.
* `level`: `"Easy"`, `"Medium"` or `"Hard"`. `minutes`: a realistic estimate.
  `daily`: true for groups 1–5 and 8. `parts`: 1, or 3 for mock rounds.

## How the judge runs things

* `python judge.py <id>` runs `pytest problems/<dir>/test_problem.py` with
  `PYTHONPATH=<backend-prep root>:<problem dir>`, so tests and the candidate's
  file can `import kit` and `import problem_api` (and read `data/` through
  `Path(__file__)` in problem_api.py, **not** relative to cwd; cwd is a
  temporary directory).
* The candidate's file is loaded through the **`sol` fixture** (a fresh module
  for every test). Tests call `sol.some_function(...)`. A `clock` fixture gives
  a fresh `kit.FakeClock`. Pytest's `tmp_path` and `monkeypatch` work as usual.
* Each test's **docstring is the case name shown to the user**. Write it as the
  expected behaviour: `"""A 503 on page 2 raises ApiError(503)"""`. Every test
  needs one.
* Put helpful messages on asserts (`assert x == y, "why this matters"`).
  They're what the user sees when a case fails.
* Mock rounds: name tests `test_part1_...`, `test_part2_...`, `test_part3_...`.
  In `problem.md`, put a line `<!-- part 2 -->` before the Part 2 section and
  `<!-- part 3 -->` before Part 3. The UI reveals a part once the previous
  part's tests pass.
* Use `../.venv/bin/python` (Python 3.12, has fastapi, httpx, pydantic, pytest,
  python-multipart, uvicorn; **no pandas**). Write code that also works on 3.10.

## The kit (read `kit/mockapi.py` and `kit/clock.py`)

* `MockAPI(clock=..., latency_s=..., real_latency_s=...)`: route handlers with
  `@api.route("GET", "/v1/things/{thing_id}")`; `api.client()` gives an
  `httpx.Client`; `api.async_client()` an `httpx.AsyncClient`; `api.log` /
  `api.calls(method, path)` record requests; `api.script(key, [...])` and
  `api.random_faults(...)` inject 5xx, `"429:N"`, `"timeout"`, `"connect"`,
  `"malformed"`; `api.max_in_flight` tracks concurrency.
* Helpers: `paginate_pages`, `paginate_offset`, `paginate_cursor`,
  `TokenIssuer` (expiring bearer tokens), `FixedWindowLimiter` (429 +
  X-RateLimit-* headers), `json_response`, `error_response`.
* `FakeClock`: `.time()`, `.sleep(s)` (instant, recorded in `.sleeps`),
  `.advance(s)`, `.set(t)`. Anything time-related in a problem takes a clock
  parameter so tests never really sleep. Only concurrency problems may use
  `real_latency_s` (keep it ≤ 0.05 s).
* Don't modify `kit/`, `judge.py`, `serve.py` or other problems. If you need
  something the kit lacks, build it in your `problem_api.py`.

## problem.md shape

1. `# <id>. <Title>`
2. A short scenario: why this exists, in a realistic product setting.
3. `## The API` / `## Input`: endpoints, envelopes, headers, sample data.
4. `## Your task`: exact signatures in a python block, then precise rules as
   bullets. Say what is raised, what is returned, ordering, tie-breaks.
5. `## Example`: concrete input → output.
6. `## Constraints`: e.g. "go through HTTP only", "use the clock, never time.sleep".
7. One to three `<details><summary>Hint N</summary> ... </details>` blocks.
8. `## Follow-up (talk it through)`: 2–3 interview-style discussion prompts.

Keep it tight: a strong candidate should be able to read it in 2 minutes.

## starter.py

A template built from `solution.py`, so practice is about the logic: imports,
public constants and type aliases, exception classes, enums, model/dataclass
fields, plain classes' `__init__`, FastAPI app setup with route decorators, and
the `__main__` block are kept; every public function and method is a signature
(plus docstring) with `raise NotImplementedError`; private helpers and
validators are left out. Problems whose given code *is* the exercise (06 fix a
broken script, 40 refactor a messy one) ship their own starter code.

That makes problem.md the whole contract: a `## Setup` section (how to get
the mock client / sample data, 2–4 lines) and, under `## Your task`, every name
the tests use (functions with signatures, exceptions with base class and
attributes, dataclasses with fields, routes), listed compactly rather than
pasted as code. Keep code in statements minimal.

## Tests

* 6–12 tests per problem (mock rounds 5–8 per part). Cover the happy path,
  ordering and tie-breaks, each edge case the statement names, and the failure
  modes. Each test must be decidable from the statement alone: never test
  behaviour the statement doesn't specify.
* Deterministic and fast: the whole file runs in well under 5 seconds. No real
  network, no real sleeps (concurrency problems excepted, tiny).
* The starter must fail at least one test (stubs raise NotImplementedError,
  so normally all of them). The reference must pass all of them.

## Verify before you finish

```
cd backend-prep
../.venv/bin/python judge.py --verify <id> [<id> ...]
../.venv/bin/python judge.py <id> --run   # with the starter in workspace/ (then delete workspace/<dir>.py)
```

Every problem must print ✔. Run the reference's `__main__` as well
(`../.venv/bin/python -c` or copy it to workspace temporarily) to check it works.
Clean up: no files left in `workspace/` and no `progress.json` from your checks.

## Tests mode: `mutants.json`

Every problem (except ones with `"tests_mode": false` in meta.json) also has a
**write-the-tests** exercise. The candidate writes pytest tests in
`workspace/<dir>_test.py` using the same `sol` fixture. Submitting runs their
suite against the reference (it must pass completely) and against each
**mutant**: the reference solution with one realistic bug planted. A mutant is
caught when at least one of their tests fails on it.

`problems/<dir>/mutants.json`:

```json
[
  {"id": "m1",
   "bug": "Drops the last page: stops when next_cursor is null without yielding that page",
   "edits": [{"find": "<exact text in solution.py>", "replace": "<buggy text>"}]}
]
```

* `find` must occur **exactly once** in `solution.py` (include enough context).
  Several edits per mutant are allowed and applied in order.
* 4–7 mutants per problem (mock rounds: 3–4 per part, 9–12 total), each a
  **different** behaviour from the statement. Make them the bugs real
  candidates write: off-by-one / stop one page early, wrong tie-break or sort
  order, wrong boundary (`<` vs `<=`, expiry at exactly the TTL), retrying a
  4xx, not retrying a 5xx/timeout, sleeping after the final attempt, wrong
  backoff formula, ignoring Retry-After, missing header/param, swallowing an
  error that should raise (or raising one that should be swallowed), forgetting
  dedupe, wrong default, mutating the caller's input, non-atomic write, a check
  done in the wrong order. Avoid trivial syntax-level mutants (`+` → `-` in a
  place nothing tests) and mutants that only change error message text.
* Every mutant must be caught by the official `test_problem.py` (the verifier
  checks this): that proves the bug is observable from the statement.
* Prefer mutants that fail fast. A mutant that loops forever only gets caught
  by the 10 s timeout, which is slow; bound it (e.g. give up after 50 pages).
* `bug` is shown to the candidate after they submit: one sentence, phrased as
  the mistake ("Retries 404s as if they were transient").

`judge.py --verify <id>` checks all of this: each mutant applies, differs from
the reference and from the other mutants, and the official tests catch it.
Optionally add `tests_starter.py` to replace the generic test-file template.
