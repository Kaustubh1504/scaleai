# Pod Staffing

Every Monday the vendor-operations team staffs this week's labelling projects from the
contributor pool. A contributor can work on several projects as long as they have
weekly hours left. Some projects are locale-specific, and some need training courses.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/contributors.csv`: `id`, `name`, `locale`, `weekly_hours`, `rating`, `active`,
  `joined`.
- `data/courses.csv`: the course log, one row per attempt (`contributor_id`, `course`,
  `result`, `taken_on`). The file is in no particular order.
- `data/projects.json`: `id`, `name`, `priority`, `seats`, `hours_per_seat`, `locale`,
  `courses`.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Cleaning

- Contributor and project ids: trim, upper-case. Locales and course ids: trim,
  lower-case. Course results: trim, lower-case (`pass` / `fail`).
- `active` is true for `y`, `yes`, `true` or `1` (any case).
- A blank `rating` means `3.0`. A rating of `0` is a real rating (probation).
- Dates are `2026-01-05`, `01/05/2026` (month/day/year) or `5 Jan 2026`. A blank
  `joined` is allowed.
- Blank entries in a project's `courses` list are ignored. A blank project `locale`
  means any locale.

### Courses

1. For each contributor and course, only the **most recent** attempt counts. If two
   attempts share a date, the one further down the file counts.
2. A contributor has a course when that attempt's result is `pass`.

### Staffing

3. Projects are staffed one at a time, **highest `priority` number first**. Equal
   priorities go in project-id order. A project with 0 seats is paused and gets nobody.
4. A contributor is eligible for a project when they are active, their locale matches
   the project's (if it has one), they have **every** course the project lists, and
   their remaining weekly hours are at least the project's `hours_per_seat`.
5. Fill the seats with the best eligible contributors: highest rating; then earliest
   `joined` (blank sorts last); then lowest id.
6. Each pick uses `hours_per_seat` of the contributor's weekly hours.

### Report

`podstaff.reports.build_report()` returns:

- `assignments`: project id → contributor ids in pick order (every project, sorted by id);
- `open_seats`: project id → unfilled seats, only for non-paused projects with any;
- `multi_project`: contributor id → sorted project ids, for each contributor staffed on
  two or more projects;
- `course_demand`: course → number of non-paused projects that list it;
- `top_course`: the course with the highest demand (ties: alphabetical).

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
