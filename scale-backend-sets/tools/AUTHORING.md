# Authoring a problem

`prob-001` is the reference example of every convention below. Read it first.

## Layout

```
prob-XXX/
  problem.json                 id, title, topics, mode, difficulty, starter, planted_bugs, package
  candidate/                   exactly what the candidate receives
    README.md                  the scenario, layout, how to run; no requirements (those are in PARTn.md)
    PART1.md PART2.md PART3.md
    conftest.py                one comment line; makes the folder importable under pytest
    <package>/                 starter code (skeleton or existing repo)
    mock_services/
      __init__.py              copy verbatim from prob-001 (finds shared/)
      clock.py                 copy verbatim from prob-001
      <problem shims>.py       e.g. llm.py with make_llm() + the keyword map
    data/                      sample inputs incl. malformed rows and edge cases
    tests/                     a passing smoke test showing how to build the thing with fakes
  interviewer/
    INTERVIEWER_NOTES.md
    RUBRIC.md
    reference/                 complete solution, same layout as candidate/ (+ its own tests/)
    hidden_tests/
      conftest.py              SOLUTION_DIR handling, fixtures, `change` marker
      fixtures/                copies of any data files the tests need
      test_part1.py test_part2.py test_part3.py
```

`problem.json` must match the manifest entry's id, topics, mode, difficulty,
starter and planted_bugs (`python tools/manifest.py sync prob-XXX` copies it in).

## Problem kinds

`manifest.json` gives every problem a `kind`. At least 60% are **api-client**:
the candidate is handed a mock API and must query it (authenticate, paginate,
handle errors and rate limits, parse nested and inconsistent JSON, join across
endpoints) to compute an answer or write results. The rest are **service**
problems (build a service; prob-001..005 are examples). `prob-006` is the
reference example of an api-client problem.

### API-client conventions

* The API is `shared.mock_rest.MockRestAPI` (Scale preset or custom resources).
  `candidate/mock_services/api.py` exposes `make_api(seed=..., clock=...)` configured
  for this problem plus a helper that returns an `httpx.Client` over its transport.
  It also documents how to run it as a real server for curl.
* `candidate/API.md` is the API documentation the candidate works from, written
  like a real provider's docs: auth, endpoints, parameters, envelopes, errors,
  the canonical schema, and a "Data quality" note. It must be enough to solve the
  problem without reading `shared/`.
* Contract: the candidate's code receives an `httpx.Client` (and a `clock`, and
  credentials) rather than building one, so tests inject the mock transport.
  Typical shape: `Client(http, client_id, client_secret, clock)` + `compute_x(client) -> dict`,
  and/or a CLI that writes a file or POSTs to the results sink.
* Messy data: API.md describes the canonical types; PARTn.md states the *semantics*
  needed for a unique answer (e.g. "a null or missing reward means unknown: exclude
  the task and list it under `unknown_reward`"). Every wire variant used must have
  exactly one sensible interpretation (numeric string -> number, `"true"`/`1` -> true,
  epoch or naive ISO -> UTC time, padded/upper-case label -> normalized label).
* Hidden tests use a **different seed** (and sometimes sizes) than the candidate's
  default, so hard-coded answers fail. They compute expected values with an
  independent oracle over `api.canonical(...)` written in `hidden_tests/conftest.py`
  (never import the reference).
* Behavioural assertions use `api.log` and the clock: e.g. after a 429 at time t
  with Retry-After r, the next request is at >= t + r; every page fetched once; at
  most N token requests; no request after a fatal 401.
* Faults in hidden tests: `FaultConfig(scripted={...})` for exact scenarios; random
  `failure_rate` only with invariant assertions.

## Part specs (PARTn.md)

* State every requirement the hidden tests check: endpoints/functions, exact
  status codes, response shapes, error behaviour, ordering, numbering, limits.
  If a hidden test asserts it, a careful reader of the PART file (plus the
  mid-part change, if delivered) must be able to know it.
* Fix the public contract the tests use (e.g. `create_app(storage_dir, llm, clock, ...)`
  or a class constructor) in the starter code, and say "keep this signature".
* Part 1 ≈ 20 min core feature + tests. Part 2 ≈ 20 min: adds an external
  dependency or new state, with error handling. Part 3 ≈ 20 min: scale/failure
  hardening, ending with 2–3 discussion prompts.
* Do not put the mid-part change in the PART file. It lives in INTERVIEWER_NOTES.md
  (verbatim wording) and its hidden tests carry `@pytest.mark.change`.

## Starter code

* **api-client skeleton**: the contract (client class + compute function stubs),
  `mock_services/api.py`, `API.md`, and a smoke test that makes one request.
* **skeleton**: the contract (`create_app`, class with method stubs) plus
  `/health` or a smoke path. Hidden tests must fail on it.
* **repo**: a small, realistic codebase (150–400 lines) with working features,
  some tests, a README, and the seams the candidate must extend. The candidate
  must read it before Part 1. Very-hard problems (71–100) carry real tech debt.
* **planted bugs** (only where the manifest says so): 1–2 realistic bugs in
  existing code that block Part 1 or Part 2 (not typos; e.g. using `time.time()`
  instead of the injected clock, an inverted comparison, a shared sqlite
  connection across threads, an off-by-one in pagination). Existing starter tests
  should not catch them. Document each in INTERVIEWER_NOTES.md: file:line,
  symptom the candidate will see, root cause, fix, hint ladder.

## Mock services

Use `shared/` (see shared/README.md); never real network. Time-dependent code
takes a `clock` and calls `clock.sleep()/time()`; tests pass `FakeClock`.
Mocks advance a FakeClock *without* recording into `clock.sleeps`, so
`clock.sleeps` contains only the code-under-test's sleeps.

For LLM faults in hidden tests, prefer `prompt_faults={"<unique phrase>": [...]}`.
It is counted per phrase, so it is robust to however the candidate words the
prompt. Don't assert exact outcomes of random fault rates (prompts differ
between candidates); assert invariants only.

If `shared/` lacks something, do not edit it from a problem; report it.

## Hidden tests

* `conftest.py`: `SOLUTION_DIR` env var (default `../reference`) inserted at
  `sys.path[0]`, then `import mock_services`; register the `change` marker;
  print the solution dir in the report header. Copy any constants the tests rely
  on (keyword maps, fixture files) so candidate edits can't change the outcome.
* One file per part. Each must pass on the reference and fail on the untouched
  starter (ideally almost every test fails on the starter).
* Test behaviour through the public contract only. Test fairness over cleverness.
* Whole suite (reference tests + hidden tests) runs offline in well under 30 s.

## Reference solution

Production quality: clear module boundaries, atomic writes where files are
state, injected clock, no swallowed errors, input validation (including path
safety for ids used in paths), and its own tests (unit + API/integration).
Lines the candidate must add (reference minus starter, excluding tests, mock_services,
blanks, comments) ≤ 360 in total and roughly ≤ 120 per part. Cut scope if over.

## INTERVIEWER_NOTES.md sections

Header (mimics / difficulty / mode / starter / planted bugs) · Setup (export
command, how to run hidden tests against the candidate) · Timeline for 60-min
mode (table) · Timeline for 30-min mode (Part 1 + start of Part 2) · Mid-part
requirement change (when, verbatim wording, what it tests, which tests) ·
Planted bugs (or "None") · Hint ladder per part (3 levels) · Common pitfalls ·
3 follow-up questions on scaling and failure, each with what a strong answer
covers · Reference solution overview + LOC per part.

## RUBRIC.md

Seven categories scored 1–4: correct execution, debugging and unblocking,
systematic thinking, production quality, testing, end-to-end ownership,
communication. For each, describe concretely what a 4 and a 2 look like for this
problem. Add a hidden-test → coverage mapping table.

## Verify

```
cd scale-backend-sets
PATH=/Users/kaustubh/Desktop/scaleai/.venv/bin:$PATH python tools/verify_problem.py prob-XXX -v
```
