# Weekly Seat Planner

Each week the ops team staffs open projects with contributors. A project needs a number
of **seats**; each seat is one contributor working `hours_per_seat` hours on it that
week. Contributors have a weekly hour budget, a region and a list of skills with levels.
This tool fills the seats and reports what could not be filled.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/contributors.csv`: `contributor_id`, `region`, `skills`, `weekly_hours`,
  `status`.
- `data/projects.csv`: `project_id`, `priority`, `region`, `skill`, `min_level`, `seats`,
  `hours_per_seat`, `status`.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Cleaning

- Contributor and project ids: trim and upper-case. Regions, skills and statuses: trim
  and lower-case.
- `skills` is a `;`-separated list of `name:level`, e.g. `python:5;sql:9`. A skill
  written without a level (`spanish`) has level 1. A skill the contributor doesn't list
  has level 0.

### Who can take a seat

1. Only contributors whose status is `active` or `trial` can be staffed. `paused` and
   `offboarded` contributors are never staffed.
2. The project's region must equal the contributor's region, or be `any`.
3. The contributor's level in the project's skill must be at least `min_level`.
4. The contributor must have at least `hours_per_seat` hours left this week.
5. A contributor takes at most one seat on any one project, but may work on several
   projects while hours remain.

### Order

6. Only `open` projects are staffed. **The higher `priority` number is more important**:
   projects are staffed from the highest priority down, ties by project id.
7. Seats on a project are filled one at a time with the best remaining candidate: highest
   level in the project's skill, then most hours left, then lowest contributor id.

### Report

`seatplan.reports.build_report()` returns:

- `assignments`: open project id → contributor ids in the order they were picked;
- `unfilled`: open project id → seats left empty;
- `skill_gaps`: skill → total unfilled seats over **open** projects needing that skill;
- `utilisation`: for each active or trial contributor, hours used ÷ weekly hours,
  rounded to 2 decimals.

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
