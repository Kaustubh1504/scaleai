# Annotator Tripwire

Support-ticket summarisation tasks are labelled by a pool of contract annotators. Each
submission is a short free-text summary of a ticket plus the time the annotator spent on
it. This tool scans one batch for two fraud signals, **rushing** (submissions far faster
than everyone else on the same task) and **copying** (the same answer as another
annotator on the same task), and produces the review report that the trust team reads.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/annotators.csv`: the registry (`annotator_id`, `name`, `status`).
- `data/submissions.csv`: one row per submission (`annotator_id`, `task_id`, `answer`,
  `duration_s`, `submitted_at`).

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Cleaning

- Annotator ids: trim and upper-case (` a04` → `A04`). Task ids: trim and lower-case
  (` T1 ` → `t1`).
- `status` is compared after trimming, ignoring case. Only `active` annotators are
  reported. Submissions from anyone else (inactive, suspended, unknown) are ignored
  completely, for every signal.
- `submitted_at` is `2026-04-02 09:00`, `04/02/2026 09:00` (month/day/year) or
  `2026-04-02T09:00:00`. Submissions before `2026-04-01 00:00` belong to an earlier
  batch and are ignored.
- `duration_s` is `95`, `95s` or `1:35` (minutes:seconds). A blank duration means the
  submission is **untimed**: it still counts as a submission and for copying, but not
  for anything timing-related.

### Rushing

1. A task's **median** is the median duration of its timed submissions (for an even
   count, the mean of the two middle values).
2. A timed submission is **rushed** when its duration is strictly below 25% of its
   task's median.
3. An annotator's `rush_rate` is rushed ÷ timed submissions, as a percentage rounded to
   1 decimal (1 of 3 → `33.3`). With no timed submissions it is `0.0`.

### Copying

4. Two answers are the same when they match after lower-casing, collapsing runs of
   whitespace to one space, and removing trailing `.` and `!`. Blank answers never match.
5. An annotator's `shared_answers` is the number of their submissions whose answer is
   the same as at least one submission **by a different annotator** on the same task.

### Flags

6. `rushing`: at least 3 timed submissions and `rush_rate` ≥ 30.0.
7. `copying`: `shared_answers` ≥ 2.

### Report

`tripwire.report.build_report()` returns:

- `annotators`: for every active annotator, `submissions`, `timed`, `rushed`,
  `rush_rate`, `shared_answers` and `flags` (`rushing` before `copying`).
- `tasks`: for every task with at least one counted submission, `submissions` and
  `median_s`.
- `summary`:
  - `flagged`: sorted ids of annotators with at least one flag;
  - `flags_by_reason`: flag → number of annotators with it;
  - `worst_rusher`: the annotator with the highest `rush_rate` among those with at
    least one timed submission. Ties go to the lowest annotator id.

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
