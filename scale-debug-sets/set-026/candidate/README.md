# Tone Vote

Support transcripts, customer emails and product reviews are labelled for tone
(`positive`, `negative`, `neutral`) by several annotators each. Every project has its
own vote quorum and agreement bar. This tool works out which tasks reached agreement,
how often each annotator sides with the agreed label, and a per-team activity summary.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/projects.json`: project id → `min_votes`, `agreement`.
- `data/batches/<project>.csv`: one file per project (the project id is the file name),
  one row per submission: `task_id`, `annotator_id`, `label`, `submitted_at`.
- `data/teams.csv`: the team roster (`annotator_id`, `team`, `joined`), exported from
  the staffing spreadsheet. Some exports start with a UTF-8 byte-order mark; it is not
  part of the first column name.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Cleaning

- Task ids: trim and upper-case (`c-01` → `C-01`). Annotator ids, team names and
  project ids: trim and lower-case.
- Labels: trim and lower-case, then expand the short forms `pos` → `positive`,
  `neg` → `negative`, `neu` → `neutral`.
- A row with a blank label is ignored completely.
- The label `skip` means the annotator opened the task and declined to label it. A skip
  is **not a vote**.
- `submitted_at` uses one of `2026-03-09 09:00`, `2026-03-09T09:00:00`,
  `03/09/2026 09:00` (month/day/year) or `09.03.2026 09:00` (day.month.year).
- Batch files whose name is not a project in `projects.json` are ignored.

### Submissions

1. If an annotator submitted more than once for the same task, only their submission
   with the latest `submitted_at` counts. Earlier ones are discarded entirely.

### Task status

2. A task's **votes** are its non-skip submissions (after rule 1).
3. Fewer than the project's `min_votes` votes → `pending`. Exactly `min_votes` is
   enough to decide.
4. Otherwise, if two or more labels share the highest vote count → `escalated`.
5. Otherwise the top label's share (top count ÷ votes) is compared with the project's
   `agreement`. A share **at or above** `agreement` → `agreed` with that label;
   below it → `escalated`.
6. Only `agreed` tasks have a label; every other status has label `None`.

### Annotator agreement

7. For every annotator who appears in any batch (votes or skips):
   - `agreed_tasks`: number of `agreed` tasks they **voted** on (skips don't count);
   - `agreement`: how many of those votes matched the agreed label ÷ `agreed_tasks`,
     rounded to 3 decimals, or `None` if `agreed_tasks` is 0;
   - `skips`: number of tasks they skipped.

### Report

`tonevote.reports.build_report()` returns:

- `tasks`: per task id: `project`, `status`, `label`, `votes`.
- `annotators`: the rule 7 table.
- `labels`:
  - `by_project`: per project, agreed label → number of agreed tasks in **that
    project** with that label;
  - `overall`: the same count across all projects.
- `teams`: per team in `teams.csv`: `members` (sorted annotator ids on the roster) and
  `votes` (total votes cast by those members, under rules 1–2). Annotators who are not
  on the roster are left out of the team summary.

## Running

Requires Python 3.10+. No third-party packages.

```bash
python main.py                         # print the report
python -m unittest discover -s tests   # run the tests
python -m pytest tests                 # same tests, if you have pytest
```

## Rules

- Do not modify the tests or anything under `data/`.
- Do not modify code marked `# VERIFIED`; it has been reviewed and is correct.
- Everything else is fair game. Each change should be small.
