# set-001 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What happens end to end when build_report() runs?

`staffing/reports.py:build_report` loads `contributors.csv` and `projects.csv` through `loader.load_contributors` / `loader.load_projects`, passes both lists to `assigner.assign`, then derives `open_seats` and `bench` from the assignments. `main.py` just prints the resulting dict as JSON.

### 2. Where is the order in which projects get staffed decided?

In `assigner.project_order`. `assign()` iterates over its result one project at a time. A project with `headcount <= 0` gets an empty list and is skipped. Otherwise it builds the pool of eligible, not-yet-taken contributors and takes the first `headcount` of `rank_candidates(pool)`.

### 3. How does assign() stop a contributor being put on two projects?

It keeps a `taken` set of contributor ids. The pool for each project excludes ids already in `taken`, and the chosen ids are added to it right after each project is staffed.

### 4. What does loader._split return for a blank cell like an empty completed_courses?

An empty list. The cell is stripped, split on `;`, each part is stripped, and empty parts are dropped. So a blank cell becomes `[]`, and `" ML-101"` becomes `["ML-101"]`.

### 5. What does rank_candidates sort by, and where does a contributor without a joined date go?

Rating descending, then `joined` ascending, then id ascending. A missing `joined` is replaced with `date.max`, so at equal rating that person sorts after everyone who has a date.

### 6. What does a blank rating turn into?

`0.0`. The loader does `float(_clean(row["rating"]) or 0)`, so an empty string falls back to 0.

### 7. Who ends up on the bench?

`reports.bench` lists contributors with `available == True` whose id doesn't appear in any project's assignment list, sorted by id. Unavailable contributors are never on the bench.
