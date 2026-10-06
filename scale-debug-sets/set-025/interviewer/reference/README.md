# Weekly Hours Allocation

Each week the vendor team splits contributor hours across annotation projects. Unlike a
one-person-per-project roster, a contributor's weekly hours can be spread over several
projects, and a project can draw hours from several contributors. Who may work on what
depends on skill assessment scores and, for some projects, the contributor's region.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/contributors.csv`: `contributor_id`, `name`, `region`, `weekly_hours`, `active`.
- `data/assessments.csv`: one row per assessment attempt (`contributor_id`, `skill`,
  `score`). A contributor may attempt a skill more than once.
- `data/projects.csv`: `project_id`, `skill`, `min_score`, `hours_needed`, `priority`,
  `region`.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Cleaning

- Contributor and project ids: trim and upper-case. Regions and skills: trim and
  lower-case.
- A blank `weekly_hours` means `20`. `0` means the contributor is on leave this week.
- `active` is true for `y`, `yes`, `true` or `1` (any case); anything else is false.
- Scores are whole numbers from 0 to 100. A blank score is an unfinished attempt and is
  ignored. A contributor's score for a skill is their **best** finished attempt.
- A blank project `region` means `any`.

### Eligibility

A contributor is eligible for a project when all of these hold:

1. they are active and their weekly hours are above 0;
2. the project's region is `any`, or it equals the contributor's region;
3. their score for the project's skill is at least `min_score`.

### Allocation

4. Projects are filled one at a time in priority order. **The higher priority number is
   more important.** Ties go to the lower project id.
5. For a project, go through its eligible contributors from the highest skill score down
   (ties: more remaining hours first, then lower contributor id). A contributor with no
   hours left is skipped. Each contributor gives `min(their remaining hours, hours still
   needed)`. Stop when the project is full.
6. Hours given to a project are no longer available for later projects. A project may
   end up partly filled.

### Report

`crew.reports.build_report()` returns:

- `allocations`: project id → `{contributor_id: hours}` in the order hours were given.
  Every project appears, even with no hours.
- `unfilled`: project id → hours still needed, only for projects not fully filled.
- `utilization`: for each active contributor with weekly hours above 0, hours given ÷
  weekly hours, rounded to 2 decimals.
- `idle`: sorted ids of those same contributors who were given no hours.

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
