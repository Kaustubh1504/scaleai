# Contributor Staffing

The operations team staffs annotation projects from a pool of contributors. Each week
they export two spreadsheets, `data/contributors.csv` and `data/projects.csv`, and run
this tool to decide who works on what.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Input cleaning

- Contributor ids and project ids are case-insensitive and may have surrounding spaces.
  Normalise them to upper case (`c02 ` → `C02`).
- `skills` and `completed_courses` are `;`-separated lists. Items may have stray spaces.
  Skills compare case-insensitively. Course ids compare case-insensitively.
- A blank `rating` means `0.0`.
- `joined` uses one of three formats: `2023-02-10`, `03/15/2022` (month/day/year) or
  `5 Jan 2023`.
- `available` is true for `y`, `yes`, `true` or `1` (any case). Anything else is false.
- A blank `required_course` means the project has no course requirement.

### Assignment

1. Projects are staffed one at a time in **priority order**. Priority `1` is the most
   important project; larger numbers are less urgent. Ties are broken by project id
   (ascending).
2. A project with `headcount` 0 is paused and receives nobody.
3. A contributor is **eligible** for a project when all of these hold:
   - they are available;
   - they have the project's `required_skill`;
   - if the project has a `required_course`, they have completed that course.
4. From the eligible contributors not yet assigned elsewhere, take the best
   `headcount` people. "Best" means: highest rating first; on equal rating, the one who
   joined earliest; then lowest contributor id. A contributor without a `joined` date
   sorts after everyone with one.
5. Each contributor works on at most one project. If there are not enough eligible
   people, the project is left partly (or entirely) unstaffed.

### Report

`staffing.reports.build_report()` returns:

- `assignments`: project id → list of contributor ids, in the order they were picked.
  Every project appears, including paused ones (empty list).
- `open_seats`: project id → number of unfilled seats, only for projects with at least
  one unfilled seat. Paused projects never have open seats.
- `bench`: sorted ids of **available** contributors who were not assigned anywhere.

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
