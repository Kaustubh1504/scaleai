# Annotator Integrity Scan

Captioning tasks are paid per submission, which attracts two kinds of abuse: rushing
through tasks far faster than anyone can read the image, and copying another
annotator's answer. This tool scans a day of submissions and flags both.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/annotators.csv`: the annotator registry (`annotator_id`, `team`, `joined`).
- `data/submissions.csv`: one row per submission: `submission_id`, `annotator_id`,
  `task_id`, `started_at`, `submitted_at`, `answer`.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Cleaning

- Annotator ids: trim and lower-case (` Ann-04` → `ann-04`), in both files.
  Task ids: trim and upper-case. Submission ids: trim.
- Submissions from annotators who are not in the registry are ignored completely.
- Timestamps use one of `2026-05-04 09:00:00`, `05/04/2026 09:00:00` (month/day/year)
  or `2026-05-04T09:00:00`.
- A submission from a registered annotator is **rejected** if either timestamp is in
  any other format, or if it was submitted before it was started. Rejected submissions
  are listed in the summary and take no further part in the scan.

### Speeding

1. A submission's duration is `submitted_at − started_at` in seconds.
2. A submission is **fast** when its duration is under 20 seconds. Exactly 20 seconds is
   not fast.
3. `fast_ratio` = fast submissions ÷ the annotator's valid submissions, rounded to 3
   decimals. An annotator with `fast_ratio` of at least 0.5 is flagged `speeding`.

### Copying

4. Answers are compared after lower-casing, collapsing runs of whitespace to a single
   space, and dropping trailing `.`, `!` or `?`.
5. On one task, when **two or more different annotators** gave the same answer, each of
   them is flagged `copying` and the task is listed under `copy_tasks`. An annotator
   who submits the same answer twice on a task is not copying anyone.

### Report

`fraudscan.reports.build_report()` returns:

- `annotators`: for each registered annotator with at least one valid submission,
  `submissions`, `fast_ratio` and `flags` (sorted list).
- `summary`:
  - `flagged`: sorted ids of annotators with at least one flag;
  - `copy_tasks`: task id → sorted annotators flagged for copying on that task;
  - `rejected`: sorted ids of rejected submissions.

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
