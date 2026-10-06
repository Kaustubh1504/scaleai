# Weekly Crew Planner

Each week the delivery team fills project seats from the contributor pool. Every seat
costs the contributor a fixed number of hours from their weekly capacity, and many
projects require current course certifications. The same tool also produces a course
coverage table that training uses to decide which course to schedule next.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/contributors.csv`: `contributor_id`, `name`, `weekly_hours`, `rating`.
- `data/projects.csv`: `project_id`, `priority`, `status`, `seats`, `hours_per_seat`,
  `required_courses`.
- `data/completions.csv`: one row per course completion.
- `data/config.json`: the planning date (`as_of`) and how long a certification lasts.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Cleaning

- Contributor, project and course ids: trim and upper-case (`k02` → `K02`).
- `required_courses` is a `;`-separated list; items may have spaces; blank means none.
- `status` is `open` or `paused` (any case).
- A blank `rating` means `0.0`.
- `completed_on` uses `2026-03-10`, `06/30/2026` (month/day/year) or `Feb 02 2026`.

### Certifications

1. A completion is **current** when it is not in the future and is at most `valid_days`
   days before `as_of` (a completion exactly `valid_days` days old is still current).
   A contributor holds a course if any of their completions of it is current.

### Staffing

2. Projects are staffed one at a time by **priority: the higher number is more
   important**. Ties go to the lower project id.
3. Paused projects are skipped: they get no one and never have open seats. They are still
   listed with an empty team.
4. A contributor is **eligible** for a seat when they are not already on this project,
   they hold every required course, and their remaining weekly hours are at least the
   project's `hours_per_seat`.
5. Seats are filled one by one. Each seat goes to the eligible contributor with the
   highest rating; ties go to the one with more remaining hours, then the lower id. The
   seat's hours are deducted at once. A contributor may work on several projects.
6. If nobody is eligible, the remaining seats stay open.

### Course coverage

7. Every course that appears in a requirement or in a current certification gets a row:
   - `holders`: number of contributors who hold it (rule 1);
   - `demand`: number of **open** projects that require it.
8. `most_demanded` is the course with the highest demand; ties go to the lower course id.

### Report

`crewplan.reports.build_report()` returns `assignments` (project id → contributor ids in
pick order, every project listed), `open_seats` (project id → unfilled seats, only open
projects with at least one), `courses` (course id → `holders`, `demand`) and
`most_demanded`.

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
