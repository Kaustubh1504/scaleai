You are building a practice library of 100 debugging-interview codebases that mimic
Scale AI's "Debugging Practical" round. Read this whole spec before starting.

## The real round (what we are mimicking)
- Hosted on HackerRank, Python, 60 minutes.
- Candidate gets an unfamiliar multi-file codebase plus a "spreadsheet" of data
  (e.g. contributors, courses, projects) and numbered failing tests (Test 1 → 2 → 3).
- Candidate must find and fix ALL bugs AND explain where and why the code fails.
- Reported real example: contributor-to-project assignment by project priority,
  some projects require completed courses; Test 3 = course required by most projects.
  Reported bugs: priority sorted in the wrong direction, zero headcount treated as
  valid capacity, course completion not checked, course id read from the wrong field,
  plus two counting bugs in the Test 3 path. Six bugs total; all six needed to pass.

## Output
Create `scale-debug-sets/` with `set-001` … `set-100`. Each set contains:
- `candidate/`: the buggy repo (this is all the candidate sees)
- `interviewer/`: answer key, notes, scoring sheet, and the reference solution
- `manifest.json` at the root: one entry per set with id, domain, length,
  bug list (type + file), status (pending/built/verified)

Two lengths, alternating so the library stays balanced:
- MINI (30 min): 3 bugs, 2 test files, 4–6 source files
- FULL (60 min): 6 bugs, 3 test files, 6–9 source files
Make 50 MINI and 50 FULL.

## Candidate repo requirements
- Python 3.10+, standard library only. Tests use `unittest` (must also run under pytest).
- `README.md` containing: the scenario, a precise spec (the spec is the source of
  truth for "correct"), run commands, and rules (do not modify files marked
  `# VERIFIED`, tests, or data).
- `data/` with CSV and/or JSON files (10–40 rows) including realistic messiness:
  stray whitespace, mixed-case ids, blank cells, mixed date formats.
- Package layout like: models.py, loader.py, core logic (2–3 files), reports.py,
  utils.py, main.py. Vary layouts across sets.
- 1–2 files or functions marked `# VERIFIED` that are genuinely correct, at least one
  of which LOOKS suspicious (a red herring).
- Tests assert on end-to-end outputs (like the real round), not on individual helpers.
- At least one bug must be masked: it only becomes visible after an earlier bug is
  fixed, or it only shows up in the Test 3 report.
- Vary priority conventions across sets (sometimes 1 = most important, sometimes the
  higher number is more important). The candidate must read the spec and data.
- NO hints anywhere: no comments, names, or TODOs that point at bugs. Misleading-but-
  plausible comments are allowed (e.g. "# most important first" on a wrong sort).

## Domains (rotate; each domain used ~6–7 times with different mechanics and data)
contributor/project assignment with course requirements; annotation consensus
(majority/weighted vote, gold tasks); task queue with leases and expiry; review queue
and task lifecycle state machine; LLM eval scoring pipeline (aggregation, retries,
parsing model output); CSV/JSON data ingestion and validation with dedupe;
per-tenant rate limiting and usage billing; annotator fraud detection (timing
outliers, duplicate answers); load balancer with worker states; job scheduler with
priorities and retries; leaderboard and ranking; seat/slot reservation with holds;
caching layer with TTL; payout calculation for contributors; dataset split and
sampling (train/val/test, stratified).

## Bug taxonomy (each set uses a different mix; spread bugs across different files)
sort direction or priority meaning flipped; wrong tie-break; falsy-zero (`x or default`);
`"".split()` producing `[""]`; `bool("false")`; off-by-one (`<` vs `<=`, slices, ranges);
wrong field/attribute/key; id normalization mismatch (case/whitespace); state never
reset per loop iteration; mutable default argument; aliasing/shallow copy; class
attribute shared across instances; modifying a list while iterating; aggregation
without dedupe; counting the wrong subset (e.g. paused/inactive items); Counter or
groupby misuse; string vs int comparison; integer division; float rounding; Enum vs
string comparison; early return/break inside a loop; `or` precedence
(`x == "a" or "b"`); swallowed exception; retry count off-by-one; wrong exception
order; timedelta `.seconds` vs `total_seconds()`; ms vs s units; inclusive/exclusive
time windows; cache key missing a parameter.
Every fix must be 1–3 lines. Bugs must be realistic refactoring mistakes, not tricks.

## Interviewer folder (per set)
- `ANSWER_KEY.md`: for each bug, the symptom (which test and what output),
  file:function, WHY it fails in one or two sentences, the fix as a small diff, and
  which test it unblocks.
- `INTERVIEWER_NOTES.md`: timeline (MINI: 0–3 orient, 3–25 debug, 25–30 explain;
  FULL scaled to 60), a 3-level hint ladder per bug (nudge → area → exact line),
  and two "why did that fix work?" probe questions.
- `SCORING.md`: bugs found, minutes per bug, hints used, and explanation quality
  (1–4: symptom → location → why → fix stated clearly).
- `reference/`: the fully correct codebase.

## Build process (mandatory, per set)
1. Write the correct reference implementation and tests first; confirm all tests pass.
2. Define each bug as an exact (file, old_text, new_text) edit and store it in the manifest.
3. Mutation check: apply EACH bug alone to a copy of the reference and confirm at least
   one test fails. Then apply ALL bugs and confirm the failing pattern matches the
   design (masked bugs stay hidden until earlier ones are fixed).
4. Confirm no test takes over 2 seconds and nothing hangs.
5. Generate `candidate/` from reference + all bugs; grep it for leftover hints.
6. Mark the set verified in the manifest only after steps 1–5 pass.
Write a reusable `tools/verify_set.py` that performs steps 3–5 for any set.

## Workflow
- Work in batches of 5 sets. After each batch, print a summary table (set, domain,
  length, bug types) and stop so I can review before continuing.
- The library must be resumable from `manifest.json` across sessions.
- Ramp difficulty: sets 1–20 easier (obvious symptoms), 21–70 medium, 71–100 hard
  (masked bugs, red herrings, interacting bugs, larger data).
- No two sets may share the same domain + bug-mix combination.
- Finally, zip each set's `candidate/` and `interviewer/` folders separately.

## Additional coverage (required)
Add these domains to the rotation (reduce others proportionally):
- Model-endpoint client code: request building, response parsing, retries, pagination
  of API results, against a local mock LLM/HTTP server (at least 12 sets).
- Bounding-box annotation QA (IoU, matching predictions to ground truth, thresholds).
- Text-span/NER labeling (character offsets, overlapping spans, merging annotators).
- RLHF preference data (pairwise comparisons, win rates, Elo or Bradley-Terry style
  ranking aggregation).
- SFT dataset formatting (chat turns, roles, truncation to token limits).
- Robotics/physical-AI episode data (frame timestamps, sensor sync, episode
  validity filters).
- Human-in-the-loop routing (model confidence threshold → human review queue).

Add these bug types to the taxonomy:
missing `await`; `asyncio.gather` without `return_exceptions` hiding failures; shared
mutable state across async tasks; semaphore created but not used; wrong pagination
cursor handling (skipping or repeating a page); ignoring HTTP status codes; BOM or
encoding issues in CSV; JSON serialization of datetime/set; IoU computed with
inclusive/exclusive coordinate mistakes; span-offset off-by-one.


Start with set-001 to set-005.

## Format update (from a current Scale engineer)
- Default format: each failing test corresponds to exactly ONE bug; fixing it makes
  that test pass. Use this for 70% of sets; keep the multi-bug-per-test format for 30%.
- Add a CONTEXT_ASSISTANT.md to each interviewer folder: 5–8 example questions the
  candidate could ask an AI assistant about files and functions, with the answers
  (to practice asking for context rather than solutions).

### How this is applied
- "Test" means an individual test case (test method), so the MINI (2 test files) and
  FULL (3 test files) layouts stay the same. A one-to-one set has exactly one failing test
  case per bug, numbered in fix order.
- Each set records `format` in the manifest: `one_to_one` (70 sets) or `multi` (30 sets).
  Multi sets: 001–006, 009, 013, 016, 019, 022, 025, 028, 031, 034, 038, 041, 045, 048,
  051, 056, 059, 063, 066, 071, 074, 077, 080, 086 and 090. That is 15 MINI and 15 FULL, and
  every domain has at least one.
- One-to-one verification: each bug applied alone fails exactly its own test. All bugs
  applied fail exactly the bug tests. Removing any single bug from the full set makes
  exactly that bug's test pass.
- Masking in one-to-one sets: a bug can't hide behind another bug without breaking the
  one-test-per-bug rule. So the masking requirement becomes "the bug only shows up in the
  last (report) test file", plus red herrings. At least one bug's test must be in the last
  test file. Masking where one bug hides another stays a feature of `multi` sets.
- CONTEXT_ASSISTANT.md answers describe what the candidate code does. They never say
  whether the code is correct and never give a fix. The Q&A is authored in each set's
  `bugs.json` (`context_qa`) and rendered with the other interviewer docs.
