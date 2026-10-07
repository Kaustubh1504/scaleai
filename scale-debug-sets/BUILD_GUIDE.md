# Build guide for set builders

Read this fully, then read `/Users/kaustubh/Desktop/scaleai/debugging.md` (the library
spec, including the "Format update" section at the end). The spec wins where the two differ.

## Gold examples: study before building

`set-001` … `set-005` are finished, verified sets. Before writing anything, read at least
`set-002/interviewer/bugs.json`, `set-002/interviewer/reference/` (README, package, tests,
data) and `set-004` (the endpoint client + mock server). Match their quality: a realistic
small codebase, a precise README spec, messy data, end-to-end tests, and bugs that are
realistic refactoring slips.

## Your plan entry

`manifest.json` already holds each set's `domain`, `length` (MINI/FULL), `difficulty`
(easy/medium/hard) and `format` (one_to_one/multi). Use them exactly. Don't edit
`manifest.json` by hand, don't run `tools/plan.py`, don't touch `tools/` or other sets'
folders. Only write inside your own `set-NNN/` folders.

## Per-set workflow

Python: `/Users/kaustubh/Desktop/scaleai/.venv/bin/python` (3.12, has pytest). Run the
tools from `/Users/kaustubh/Desktop/scaleai/scale-debug-sets`.

1. Write `set-NNN/interviewer/reference/`:
   - `README.md`: the scenario, a precise spec (the source of truth), run commands, and
     rules. Copy the run commands and rules sections from set-002. Never use the words bug,
     broken, wrong, incorrect, todo, fixme, hack or "off by one" anywhere in the candidate
     files. Say "The test suite is currently failing…" the way the examples do.
   - `<package>/__init__.py` plus the source modules; `main.py` at the root.
     MINI = 4–6 source files, FULL = 6–9 (root `main.py` counts; `__init__.py` doesn't).
     Use a distinctive package name that does not shadow the stdlib (`queue`, `json`,
     `http`, `email`, `types`, `test`, etc. are banned).
   - `data/`: CSV and/or JSON, 10–40 rows **per file**, with messiness: stray whitespace,
     mixed-case ids, blank cells, mixed date formats.
   - `tests/__init__.py` plus `tests/test_1_*.py`, `tests/test_2_*.py` (+ `test_3_*.py`
     for FULL): unittest, end-to-end assertions on outputs, < 2 s each, no network
     except a local mock server you start in `setUpClass` (see set-004's
     `tests/mock_server.py`; helpers in tests/ that aren't `test_*.py` are fine).
   - 1–2 functions marked with a line `# VERIFIED` directly above `def`/`class`. They must
     be genuinely correct, and at least one must look suspicious (a red herring).
   - Python 3.10+, standard library only.
   - Run the reference with unittest and pytest and check every expected value **by
     hand against your README spec** before you trust it.
2. Write `set-NNN/interviewer/bugs.json` (schema below). Every bug is an exact
   (file, old, new) edit, and the fix is 1–3 lines. `old` must occur exactly once in that file.
   Spread the bugs across files (at least ceil(n/2) distinct files).
3. `../.venv/bin/python tools/verify_set.py set-NNN`. Iterate (data, tests, bug edits)
   until it prints `VERIFIED`. Then read `set-NNN/interviewer/verification.json` and make
   each bug's `symptom` text match what actually fails.
4. Re-run `verify_set.py`, then `../.venv/bin/python tools/render_docs.py set-NNN`.
5. Skim `set-NNN/candidate/` to confirm nothing gives away a bug (names, comments).
   Misleading-but-plausible comments are allowed.
6. Make sure no name goes unused because of a bug, e.g. an import or helper that only the
   reverted line used. A linter would flag it and point straight at the change. If a bug
   orphans an import, add it to the bug's `extra` edits (`[{"file", "old", "new"}]`) to drop
   that import too. If it orphans a helper, reshape the bug so the helper is still called.

## Formats

**one_to_one** (default): each bug makes exactly one test method fail, and fixing that bug
alone makes that test pass. The verifier checks this as follows:
- each bug alone fails only its `test`;
- all bugs together fail exactly the bug tests;
- removing any one bug passes exactly its test.
Design tips:
- Give each bug its own test method that asserts on one slice of the end-to-end output,
  e.g. one project's assignments, one report field, one request's attempts.
- Make the other tests assert on slices that bug can't reach.
- Choose data so the bugs don't interact. Other test methods in the files should pass in
  every state.
- Name the bug tests in fix order (`test_1_...` in file 1, etc.).
- In these sets "masked" means: at least one bug's test is in the **last** test file
  (the report). `masked_by` is not allowed.

**multi**: tests may fail for several bugs. You need at least one real mask (`masked_by`:
the test output is identical with or without the bug while the masking bug is present)
or `visible_only_in` the last test file. Prefer a real mask (see set-001/002/003/004).
Set `design.all_bugs_failing_files`.

## Difficulty

- **easy**: obvious symptoms, simple data.
- **medium**: subtler symptoms. Red herrings that really look like the problem. Bugs in
  less obvious files (loader/utils/models). Data around 20–40 rows.
- **hard**: two VERIFIED red herrings, symptoms far from the cause, and several data
  files (each still ≤ 40 rows). In multi sets, bugs that interact or mask each other.
  FULL hard sets should use 8–9 source files.

## Bug type slugs (use exactly these in `type`)

sort-direction, wrong-tie-break, falsy-zero, empty-split, bool-from-string, off-by-one,
slice-bounds, wrong-field, id-normalization, state-not-reset, mutable-default,
aliasing-shallow-copy, shared-class-attribute, mutate-while-iterating, missing-dedupe,
counting-wrong-subset, groupby-misuse, counter-misuse, string-vs-int, integer-division,
float-rounding, enum-vs-string, early-return, or-precedence, swallowed-exception,
retry-off-by-one, exception-order, timedelta-seconds, ms-vs-s, time-window-boundary,
cache-key-missing-param, missing-await, gather-hides-failures, async-shared-state,
semaphore-unused, pagination-cursor, ignoring-http-status, csv-bom-encoding,
json-serialization, iou-inclusive-exclusive, span-offset-off-by-one

Domain musts:
- **endpoint_client**: an asyncio client (stdlib asyncio; HTTP via
  `asyncio.to_thread(urllib…)` or `asyncio.open_connection`) against a local mock server
  in tests/. Each set has at least 2 of {missing-await, gather-hides-failures,
  async-shared-state, semaphore-unused}, plus at least 1 of {pagination-cursor,
  ignoring-http-status, retry-off-by-one}. Vary the endpoint: completions, embeddings,
  batch jobs, a paginated dataset API, streaming chunks, and so on.
- **ner_spans**: at least one span-offset-off-by-one.
- **bbox_qa**: at least one iou-inclusive-exclusive, or a coordinate-convention mistake.
- **data_ingestion_dedupe**: at least one csv-bom-encoding or missing-dedupe.
- **cache_ttl**: at least one cache-key-missing-param or time-window-boundary.
- Vary priority conventions: say in the README whether 1 or the higher number is the most
  important.
- No two sets may share domain + the same multiset of bug types. The verifier rejects
  clashes; if you hit one, change a bug.
- Vary mechanics and layout from the existing sets of the same domain. Look at their
  READMEs first, so your scenario is clearly different.

## bugs.json schema

```json
{
  "id": "set-NNN", "title": "...", "domain": "<manifest>", "length": "MINI|FULL",
  "difficulty": "<manifest>", "format": "<manifest>", "package": "<pkg dir>",
  "scenario": "one or two sentences for the interviewer",
  "design": {"all_bugs_failing_files": ["test_1_x", "test_2_y"]},
  "verified": [{"file": "pkg/x.py", "symbol": "func_name", "why_correct": "..."}],
  "bugs": [{
    "id": "B1", "title": "short", "type": "<slug>", "file": "pkg/x.py",
    "function": "func or Class.method",
    "test": "test_1_x.TestClass.test_method",
    "old": "exact reference text", "new": "buggy text",
    "masked_by": ["B2"], "visible_only_in": ["test_3_x"],
    "symptom": "which test fails and what it shows (from verification.json)",
    "why": "1-2 sentences", "unblocks": "which test passes after the fix",
    "hints": ["nudge", "area", "exact line"],
    "probes": ["why did that fix work? question", "second probe"]
  }],
  "context_qa": [{"q": "...", "a": "..."}]
}
```

- `test` is required in one_to_one sets and optional in multi sets.
- `masked_by` and `visible_only_in` are for multi sets only, and optional there.
- `design.all_bugs_failing_files` is required in multi sets.
- List bugs in the recommended fix order.
- `context_qa` holds 5–8 questions a candidate might ask an AI assistant about files and
  functions (flow, what a helper returns, data shape, mock-server behaviour). The answers
  are accurate for the **candidate** code but never say whether it is correct and never
  give a fix. Prefer "where/how" questions over quoting a buggy expression.

## Finish

Report each set as: `set-NNN | domain | length | format | bug types | VERIFIED or not`.
List any tooling problems you hit. Don't edit tools/; describe the problem instead.
