# set-049 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. How does staff() pick each seat?

For each project from project_order it loops until the seats are filled: it builds a pool of contributors not already picked for this project who pass `can_take`, and takes the `min` by `(-skill_level, -remaining, id)`. The winner's hours_used goes up by hours_per_seat.

### 2. What does parse_skills return for 'math:6;spanish'?

A list of (name, level) tuples in written order: [('math', 6), ('spanish', 1)]. Blank parts are skipped and names are lower-cased.

### 3. What checks are in can_take?

`is_available(contributor)`, region equal to the contributor's or 'any', `skill_level(contributor, project.skill) >= project.min_level`, and `remaining >= hours_per_seat`, combined with `and`.

### 4. How is unfilled computed?

In build_report, for every project in projects.csv: seats minus the number of ids in `assignments.get(project_id, [])`. The report's `unfilled` section is then limited to the ids in `assignments`.

### 5. Which contributors appear in utilisation?

Those for which `is_available` is truthy and weekly_hours is non-zero, sorted by id, with hours_used / weekly_hours rounded to 2 decimals.

### 6. Is Contributor.remaining stored or computed?

Computed: a property returning weekly_hours - hours_used, so it reflects seats already taken earlier in the run.
